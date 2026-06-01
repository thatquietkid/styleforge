"""
Catalog Microservice
Manages user-uploaded images with quota tracking.
E-commerce functionality (categories, products) has been removed.
"""
import os
import sys
import uuid
from datetime import datetime
from typing import List, Optional

import aiofiles
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import settings
from common.database import get_db
from common.models import Image, ImageQuota, ImageType
from common.audit_client import fire_audit

app = FastAPI(title="Styleforge Catalog Service", version="1.0.0")

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

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files at /uploads/<filename>
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ImageResponse(BaseModel):
    id: int
    user_id: int
    url: str
    image_type: str
    prompt: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class QuotaResponse(BaseModel):
    used: int
    limit: int
    remaining: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id(request: Request) -> int:
    uid = request.headers.get("x-user-id")
    if not uid:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Authentication required.", "code": "unauthorized"},
        )
    try:
        return int(uid)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid authentication token.", "code": "unauthorized"},
        )


def _image_to_dict(img: Image) -> dict:
    return {
        "id": img.id,
        "user_id": img.user_id,
        "url": img.file_path,
        "image_type": img.image_type.value if img.image_type else "upload",
        "prompt": img.prompt,
        "created_at": img.created_at,
    }


async def _check_and_increment_quota(user_id: int, db: AsyncSession) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    result = await db.execute(
        select(ImageQuota).where(ImageQuota.user_id == user_id, ImageQuota.date == today)
    )
    quota = result.scalar_one_or_none()

    if not quota:
        quota = ImageQuota(user_id=user_id, date=today, count=1)
        db.add(quota)
    else:
        if quota.count >= settings.daily_image_quota:
            raise HTTPException(
                status_code=429,
                detail={
                    "detail": f"Daily image upload limit of {settings.daily_image_quota} reached. Try again tomorrow.",
                    "code": "quota_exceeded",
                    "limit": settings.daily_image_quota,
                },
            )
        quota.count += 1

    await db.flush()
    return quota.count


# ---------------------------------------------------------------------------
# Image upload endpoint
# ---------------------------------------------------------------------------

@app.post("/api/v1/catalog/images/upload", response_model=ImageResponse, status_code=201)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image file. Enforces MIME type, size, and daily quota."""
    user_id = _get_user_id(request)

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": f"Unsupported file type '{file.content_type}'. Accepted: JPEG, PNG, WebP.",
                "code": "invalid_file_type",
                "allowed": list(ALLOWED_MIME),
            },
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "detail": "File exceeds the 5 MB size limit.",
                "code": "file_too_large",
                "max_bytes": MAX_FILE_SIZE,
            },
        )

    quota_count = await _check_and_increment_quota(user_id, db)

    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(contents)

    db_image = Image(
        user_id=user_id,
        file_path=f"/uploads/{filename}",
        image_type=ImageType.upload,
    )
    db.add(db_image)
    await db.commit()
    await db.refresh(db_image)

    fire_audit("catalog", "INFO", "Image uploaded", {
        "user_id": user_id,
        "image_id": db_image.id,
        "filename": filename,
        "quota_used": quota_count,
    })
    return _image_to_dict(db_image)


# ---------------------------------------------------------------------------
# Image retrieval endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/catalog/images/me", response_model=List[ImageResponse])
async def my_images(
    request: Request,
    image_type: Optional[str] = Query(None, description="Filter by type: upload or generated"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all images (uploaded and generated) belonging to the current user."""
    user_id = _get_user_id(request)

    query = (
        select(Image)
        .where(Image.user_id == user_id)
        .order_by(Image.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if image_type:
        try:
            type_filter = ImageType(image_type)
            query = query.where(Image.image_type == type_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": f"Invalid image_type '{image_type}'. Allowed values: upload, generated.",
                    "code": "invalid_filter",
                },
            )

    result = await db.execute(query)
    images = result.scalars().all()
    return [_image_to_dict(img) for img in images]


@app.get("/api/v1/catalog/images/quota", response_model=QuotaResponse)
async def get_quota(request: Request, db: AsyncSession = Depends(get_db)):
    """Return current user's image upload quota for today."""
    user_id = _get_user_id(request)
    today = datetime.now().strftime("%Y-%m-%d")
    result = await db.execute(
        select(ImageQuota).where(ImageQuota.user_id == user_id, ImageQuota.date == today)
    )
    quota = result.scalar_one_or_none()
    used = quota.count if quota else 0
    return {
        "used": used,
        "limit": settings.daily_image_quota,
        "remaining": max(0, settings.daily_image_quota - used),
    }


@app.get("/api/v1/catalog/images/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a single image by ID. Only accessible by the owning user."""
    user_id = _get_user_id(request)
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == user_id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Image not found or does not belong to you.", "code": "not_found"},
        )
    return _image_to_dict(img)


@app.delete("/api/v1/catalog/images/{image_id}", status_code=204)
async def delete_image(image_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete an image. Only the owning user may delete their images."""
    user_id = _get_user_id(request)
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == user_id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Image not found or does not belong to you.", "code": "not_found"},
        )

    # Remove file from disk
    disk_path = os.path.join(UPLOAD_DIR, os.path.basename(img.file_path))
    if os.path.exists(disk_path):
        try:
            os.remove(disk_path)
        except OSError:
            pass  # Non-fatal – DB record is still removed

    await db.delete(img)
    await db.commit()
    fire_audit("catalog", "INFO", "Image deleted", {"user_id": user_id, "image_id": image_id})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/v1/catalog/health")
async def health():
    return {"status": "ok", "service": "catalog"}


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
    fire_audit("catalog", "ERROR", str(exc), {"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "code": "internal_error"},
    )
