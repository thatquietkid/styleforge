"""
Gen-AI Microservice
Handles:
  - Style Critique: Upload an outfit image → Ollama qwen3.5:9b returns a structured markdown critique.
  - Scratch/Sketch Generation: Forward to Colab inference backend.

Credit system enforced on every chargeable endpoint.
All significant events are audited via fire_audit().
Responses (critiques) are persisted to the database.
"""
import io
import os
import sys
import uuid
import base64
import aiofiles
from typing import Optional
from pydantic import BaseModel

import httpx
from PIL import Image as PILImage
from fastapi import Depends, FastAPI, HTTPException, Request, File, UploadFile, Form, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import settings
from common.database import get_db
from common.models import Image, ImageType, User, StyleCritique, CreditTransaction, FabricSimulation
from common.audit_client import fire_audit

app = FastAPI(title="Styleforge Gen-AI Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COLAB_URL = os.environ.get("COLAB_URL", "https://labrador-pretended-lettuce.ngrok-free.dev")
UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"),
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Fashion critique prompt — mirrors the structured format from ai.py
_CRITIQUE_PROMPT = (
    "You are an elite Fashion Creative Director and Stylist. Your tone is sharp, editorial, and highly actionable. "
    "Analyze ONLY the fashion garments and styling of the model in this image.\n\n"
    
    "[CRITICAL CONSTRAINT]: Isolate the subject. Completely IGNORE the background, walls, floor, tiles, "
    "and environment. Act as if the model is floating on a transparent background. "
    "Do NOT mention lighting or setting. Critique ONLY the clothes, fit, fabrics, accessories, and shoes.\n\n"
    
    "INSTRUCTIONS: Output EXACTLY the markdown structure below. Replace the bracketed text `[like this]` "
    "with your expert analysis. Do NOT include the brackets in your final response. "
    "Do NOT output any introductory greetings or conversational filler. Start immediately with the first header.\n\n"
    
    "### 1. The Core Issue\n"
    "- [State the single biggest flaw inherent to the outfit or garment choices holding this look back from a premium/high-end aesthetic. Maximum 2 sentences. Focus solely on the clothes.]\n\n"
    
    "### 2. Aesthetic Breakdown (Garment Critique)\n"
    "- **Color Harmony:** [Analyze the interplay of colors specifically between the garments, shoes, and accessories.]\n"
    "- **Fit & Silhouette:** [Evaluate how the garments drape, the cut proportions, volume, and tailoring on the body.]\n"
    "- **Sartorial Styling & Textures:** [Critique the fabric interactions, styling choices like tucks or rolls, and the visual weight of the footwear.]\n"
    "- **Model Posture & Presentation:** [Assess how the model's physical presentation affects the drape and attitude of the look.]\n\n"
    
    "### 3. Execution Plan (Actionable Fixes)\n"
    "- **The Garment Swap:** [Suggest replacing one specific piece with a better alternative to elevate the look.]\n"
    "- **The Tailoring/Fit Adjustment:** [Provide one actionable styling tweak for how the current clothing should be sized, hemmed, tucked, or rolled.]\n"
    "- **The Accessory/Footwear Refinement:** [Recommend one specific change to the shoes or accessories to balance the overall silhouette.]"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id(request: Request) -> Optional[int]:
    """Extract authenticated user ID from gateway-injected header."""
    uid = request.headers.get("x-user-id")
    if not uid:
        return None
    try:
        return int(uid)
    except ValueError:
        return None


def _error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "code": code},
    )


def _preprocess_image(image_bytes: bytes, max_dim: int = 768) -> str:
    """
    Resize the image (preserving aspect ratio) to reduce VLM token count,
    convert to JPEG at quality 80, and return base64-encoded string.
    This dramatically speeds up qwen3.5:9b inference.
    """
    with PILImage.open(io.BytesIO(image_bytes)) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), PILImage.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("utf-8")


async def _get_user_or_404(user_id: int, db: AsyncSession) -> User:
    """Fetch a User by ID, raising 404 if not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise _error(404, "User not found.", "user_not_found")
    return user


async def _check_and_deduct_credits(
    user: User,
    cost: int,
    description: str,
    service: str,
    db: AsyncSession,
) -> int:
    """
    Verify the user has enough credits, deduct them, record a CreditTransaction,
    and return the new balance.

    Raises HTTP 402 if insufficient credits.
    """
    if user.credits < cost:
        raise _error(
            402,
            f"Insufficient credits. You need {cost} credits but have {user.credits}.",
            "insufficient_credits",
        )
    user.credits -= cost
    new_balance = user.credits

    tx = CreditTransaction(
        user_id=user.id,
        amount=-cost,
        description=description,
        service=service,
        balance_after=new_balance,
    )
    db.add(tx)
    # Commit is done by the caller after all DB objects are added together.
    return new_balance


async def _save_generated_image(
    img_bytes: bytes,
    user_id: Optional[int],
    prompt: Optional[str],
    suffix: str,
    db: AsyncSession,
) -> Optional[dict]:
    """Save generated image bytes to disk and create an Image DB record."""
    try:
        filename = f"gen_{suffix}_{uuid.uuid4().hex}.png"
        filepath = os.path.join(UPLOAD_DIR, filename)
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(img_bytes)

        if user_id is not None:
            db_image = Image(
                user_id=user_id,
                file_path=f"/uploads/{filename}",
                image_type=ImageType.generated,
                prompt=prompt,
            )
            db.add(db_image)
            await db.commit()
            await db.refresh(db_image)
            return {
                "id": db_image.id,
                "user_id": user_id,
                "url": db_image.file_path,
                "image_type": "generated",
                "prompt": prompt,
                "created_at": db_image.created_at,
            }
    except Exception as e:
        fire_audit("genai", "WARN", f"Failed to persist generated image to DB: {e}", {
            "user_id": user_id,
        })
    return None


async def _preflight_ollama() -> None:
    """
    Check that the local Ollama daemon is reachable before sending a heavy
    image payload. Raises HTTP 503 with code 'ollama_unavailable' if not.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            # Verify the required model is available
            tags = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in tags]
            model_short = settings.ollama_model.split(":")[0]
            available = any(
                settings.ollama_model in n or model_short in n
                for n in model_names
            )
            if not available:
                raise _error(
                    503,
                    f"Model '{settings.ollama_model}' is not pulled in Ollama. "
                    f"Run: ollama pull {settings.ollama_model}",
                    "ollama_model_missing",
                )
    except HTTPException:
        raise
    except Exception:
        raise _error(
            503,
            "Ollama is not running or unreachable. Please start Ollama with "
            f"'ollama serve' and ensure '{settings.ollama_model}' is pulled.",
            "ollama_unavailable",
        )


async def _call_ollama_critique(image_b64: str) -> str:
    """
    Send a base64 image to Ollama and return the markdown response.
    Uses the /api/chat endpoint with a single user role message containing the
    full premium critique prompt instructions to ensure proper format and vision compatibility.
    """
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {
                "role": "user",
                "content": _CRITIQUE_PROMPT,
                "images": [image_b64]
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.6,
            "num_predict": 4096,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            # Point to the /api/chat endpoint
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Parse the chat response structure correctly
            response_text = data.get("message", {}).get("content", "").strip()
            
            if not response_text:
                raise _error(502, "Ollama returned an empty response.", "ollama_empty_response")
            return response_text
            
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise _error(504, "Style critique timed out. The model took too long. Please try again.", "ollama_timeout")
    except httpx.HTTPStatusError as e:
        raise _error(502, f"Ollama API error: {e.response.status_code}", "ollama_error")
    except Exception as e:
        raise _error(502, f"Failed to communicate with Ollama: {str(e)}", "ollama_error")


# ---------------------------------------------------------------------------
# Endpoints — Style Critique
# ---------------------------------------------------------------------------

@app.post("/api/v1/genai/analyze/style-critique")
async def analyze_style_critique(
    request: Request,
    image: UploadFile = File(..., description="Fashion outfit image (JPEG/PNG/WebP, max 5 MB)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an outfit image to receive a structured AI fashion critique powered by
    the local Ollama qwen3.5:9b vision model.

    Costs 5 credits per analysis. Requires authentication.
    The markdown response is saved to the database for future retrieval.
    """
    user_id = _get_user_id(request)
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    # --- Validate file ---
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed_types:
        raise _error(
            422,
            f"Unsupported file type '{image.content_type}'. Please upload JPEG, PNG, or WebP.",
            "invalid_file_type",
        )

    file_bytes = await image.read()
    if len(file_bytes) == 0:
        raise _error(422, "Uploaded image file is empty.", "empty_file")
    if len(file_bytes) > 5 * 1024 * 1024:
        raise _error(413, "Image exceeds the 5 MB size limit.", "file_too_large")

    # --- Fetch user and check credits ---
    user = await _get_user_or_404(user_id, db)
    cost = settings.style_critique_credits

    if user.credits < cost:
        fire_audit("genai", "WARN", "Insufficient credits for style critique", {
            "user_id": user_id,
            "credits": user.credits,
            "required": cost,
        })
        raise _error(
            402,
            f"Insufficient credits. You need {cost} credits but have {user.credits}.",
            "insufficient_credits",
        )

    # --- Preflight: verify Ollama is up and model is available ---
    await _preflight_ollama()

    fire_audit("genai", "INFO", "Style critique started", {
        "user_id": user_id,
        "filename": image.filename,
        "file_size_bytes": len(file_bytes),
    })

    # --- Preprocess image for faster VLM inference ---
    image_b64 = _preprocess_image(file_bytes)

    # --- Call Ollama ---
    markdown_text = await _call_ollama_critique(image_b64)

    # --- Save image to disk ---
    filename = f"critique_{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(file_bytes)

    # --- Deduct credits and save critique to DB atomically ---
    new_balance = await _check_and_deduct_credits(
        user=user,
        cost=cost,
        description=f"Style Critique analysis ({image.filename or 'image'})",
        service="genai",
        db=db,
    )

    critique = StyleCritique(
        user_id=user_id,
        image_path=f"/uploads/{filename}",
        markdown_response=markdown_text,
        credits_used=cost,
        model_used=settings.ollama_model,
    )
    db.add(critique)
    await db.commit()
    await db.refresh(critique)

    fire_audit("genai", "INFO", "Style critique completed", {
        "user_id": user_id,
        "critique_id": critique.id,
        "credits_used": cost,
        "credits_remaining": new_balance,
    })

    return {
        "critique_id": critique.id,
        "markdown": markdown_text,
        "image_url": critique.image_path,
        "credits_used": cost,
        "credits_remaining": new_balance,
        "model_used": settings.ollama_model,
        "created_at": critique.created_at,
    }


@app.get("/api/v1/genai/analyze/style-critique/me")
async def list_my_critiques(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of the authenticated user's style critiques."""
    user_id = _get_user_id(request)
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    result = await db.execute(
        select(StyleCritique)
        .where(StyleCritique.user_id == user_id)
        .order_by(StyleCritique.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    critiques = result.scalars().all()

    return [
        {
            "critique_id": c.id,
            "image_url": c.image_path,
            "markdown": c.markdown_response,
            "credits_used": c.credits_used,
            "model_used": c.model_used,
            "created_at": c.created_at,
        }
        for c in critiques
    ]


@app.get("/api/v1/genai/analyze/style-critique/{critique_id}")
async def get_critique(
    critique_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single style critique by ID. User must own the critique."""
    user_id = _get_user_id(request)
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    result = await db.execute(
        select(StyleCritique).where(
            StyleCritique.id == critique_id,
            StyleCritique.user_id == user_id,
        )
    )
    critique = result.scalar_one_or_none()
    if not critique:
        raise _error(404, "Critique not found or you do not have access to it.", "not_found")

    return {
        "critique_id": critique.id,
        "image_url": critique.image_path,
        "markdown": critique.markdown_response,
        "credits_used": critique.credits_used,
        "model_used": critique.model_used,
        "created_at": critique.created_at,
    }


@app.get("/api/v1/genai/credits")
async def get_credits(request: Request, db: AsyncSession = Depends(get_db)):
    """Return the authenticated user's current credit balance."""
    user_id = _get_user_id(request)
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    user = await _get_user_or_404(user_id, db)
    return {
        "credits": user.credits,
        "style_critique_cost": settings.style_critique_credits,
        "image_generation_cost": settings.image_generation_credits,
    }


# ---------------------------------------------------------------------------
# Endpoint — Scratch/Sketch Generation (credits enforced)
# ---------------------------------------------------------------------------

@app.post("/api/v1/genai/generate/scratch-or-sketch")
async def generate_scratch_or_sketch(
    request: Request,
    positive_prompt: str = Form(...),
    negative_prompt: str = Form("pale fabric, washed out colors, low quality, distorted, blurry"),
    sketch_file: UploadFile = File(...),
    target_class: str = Form("long_sleeve_outwear"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate apparel from a text prompt with an optional sketch image.
    Forwards the request to the Colab/ComfyUI inference backend.
    Costs 10 credits per generation. Requires authentication.
    """
    user_id = _get_user_id(request)
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    if not positive_prompt.strip():
        raise _error(400, "positive_prompt cannot be empty.", "validation_error")

    if sketch_file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise _error(
            422,
            f"Unsupported file type '{sketch_file.content_type}'. Use JPEG, PNG, or WebP.",
            "invalid_file_type",
        )

    file_bytes = await sketch_file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise _error(413, "Sketch file exceeds the 5 MB size limit.", "file_too_large")

    # --- Credit check ---
    user = await _get_user_or_404(user_id, db)
    cost = settings.image_generation_credits
    if user.credits < cost:
        raise _error(
            402,
            f"Insufficient credits. You need {cost} credits but have {user.credits}.",
            "insufficient_credits",
        )

    fire_audit("genai", "INFO", "Scratch/sketch generation started", {
        "user_id": user_id,
        "target_class": target_class,
        "positive_prompt": positive_prompt[:200],
    })

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Health check
        try:
            health_resp = await client.get(f"{COLAB_URL}/health", timeout=10.0)
            health_resp.raise_for_status()
            health_data = health_resp.json()
            if health_data.get("status") != "healthy" or not health_data.get("gpu", False):
                raise _error(
                    503,
                    "Inference backend is offline or lacks GPU. Please try again later.",
                    "backend_unavailable",
                )
        except HTTPException:
            raise
        except httpx.RequestError:
            raise _error(503, "Failed to reach the inference backend. Please try again later.", "backend_unavailable")

        # Forward request to Colab
        data = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "target_class": target_class,
        }
        files = {
            "sketch_file": (sketch_file.filename or "sketch.png", file_bytes, sketch_file.content_type)
        }

        try:
            generate_resp = await client.post(f"{COLAB_URL}/generate", data=data, files=files)
            generate_resp.raise_for_status()
        except httpx.RequestError:
            raise _error(503, "Inference backend failed during generation. Please try again.", "backend_error")
        except httpx.HTTPStatusError as e:
            raise _error(e.response.status_code, "External inference API returned an error.", "backend_error")

    img_bytes = generate_resp.content

    # --- Deduct credits ---
    new_balance = await _check_and_deduct_credits(
        user=user,
        cost=cost,
        description=f"Image generation: {positive_prompt[:80]}",
        service="genai",
        db=db,
    )

    # --- Persist image to disk + DB ---
    saved = await _save_generated_image(img_bytes, user_id, positive_prompt, "scratch", db)

    fire_audit("genai", "INFO", "Scratch/sketch generation completed", {
        "user_id": user_id,
        "saved_image_id": saved["id"] if saved else None,
        "credits_used": cost,
        "credits_remaining": new_balance,
    })

    return Response(content=img_bytes, media_type="image/png")


# ---------------------------------------------------------------------------
# Endpoints — Fabric Simulation
# ---------------------------------------------------------------------------

class FabricSimulateBody(BaseModel):
    fabric: str
    color: str
    weight: int
    stiffness: int


@app.post("/api/v1/genai/fabric/simulate")
async def simulate_fabric(
    request: Request,
    payload: FabricSimulateBody,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate fabric draping/physics by proxying parameters to the Colab physics engine
    via {COLAB_URL}/simulate. Enforces a 5-credit fee, persists results, and audits.
    """
    user_id = _get_user_id(request)
    if not user_id:
        raise _error(401, "Authentication required. Please sign in.", "unauthorized")

    user = await _get_user_or_404(user_id, db)

    cost = settings.fabric_simulation_credits
    await _check_and_deduct_credits(
        user=user,
        cost=cost,
        description=f"Fabric simulation: {payload.fabric}",
        service="genai",
        db=db,
    )

    # Forward to Colab at /simulate
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            colab_resp = await client.post(
                f"{COLAB_URL}/simulate",
                json={
                    "fabric": payload.fabric,
                    "color": payload.color,
                    "weight": payload.weight,
                    "stiffness": payload.stiffness,
                }
            )
            colab_resp.raise_for_status()
            colab_data = colab_resp.json()
    except httpx.TimeoutException:
        raise _error(504, "Fabric simulation timed out. The Colab backend took too long to compile physics.", "colab_timeout")
    except httpx.HTTPStatusError as e:
        raise _error(e.response.status_code, f"Colab simulation backend error: {e.response.status_code}", "colab_error")
    except Exception as e:
        raise _error(502, f"Failed to connect to Colab simulation backend: {str(e)}", "colab_unavailable")

    if not colab_data or colab_data.get("status") != "success":
        raise _error(502, colab_data.get("message", "Colab simulation failed"), "colab_simulation_failed")

    render_base64 = colab_data.get("render_base64")
    if not render_base64:
        raise _error(502, "Incomplete response: Simulated image was not generated.", "colab_empty_response")

    # Persist the simulation to database
    sim = FabricSimulation(
        user_id=user.id,
        fabric_type=payload.fabric,
        color=payload.color,
        weight=payload.weight,
        stiffness=payload.stiffness,
        render_base64=render_base64,
        credits_used=cost,
    )
    db.add(sim)

    try:
        await db.commit()
        await db.refresh(sim)
    except Exception as e:
        await db.rollback()
        raise _error(500, f"Failed to persist fabric simulation to DB: {str(e)}", "db_error")

    # Audit log
    fire_audit("genai", "INFO", f"User {user.id} successfully simulated fabric {payload.fabric}", {
        "user_id": user.id,
        "fabric": payload.fabric,
        "color": payload.color,
        "weight": payload.weight,
        "stiffness": payload.stiffness,
        "credits_used": cost,
    })

    return {
        "status": "success",
        "simulation_id": sim.id,
        "fabric": sim.fabric_type,
        "color": sim.color,
        "weight": sim.weight,
        "stiffness": sim.stiffness,
        "render_base64": sim.render_base64,
        "created_at": sim.created_at.isoformat() if sim.created_at else None,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/v1/genai/health")
async def health():
    return {"status": "ok", "service": "genai"}


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    fields = []
    for err in errors:
        loc = " → ".join(str(l) for l in err["loc"] if l != "body")
        fields.append({"field": loc, "message": err["msg"]})
    first = fields[0] if fields else {"field": "unknown", "message": "Validation error"}
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"{first['field']}: {first['message']}",
            "code": "validation_error",
            "fields": fields,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": str(detail), "code": "error"})


@app.exception_handler(Exception)
async def _global(request: Request, exc: Exception):
    fire_audit("genai", "ERROR", str(exc), {"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "code": "internal_error"},
    )
