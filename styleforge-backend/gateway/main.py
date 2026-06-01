"""
Styleforge Gateway — unified entry-point.
All Pydantic schemas are defined here so FastAPI generates a rich OpenAPI spec.
"""
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import jwt as pyjwt
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Query, Request, Security, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import settings

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Styleforge API",
    version="2.0.0",
    description="""
**Styleforge** unified gateway — all traffic enters here.

## Authentication
Protected endpoints require `Authorization: Bearer <token>`.  
Get a token from `/api/v1/auth/register` or `/api/v1/auth/login`.

## Services
| Service   | Prefix               |
|-----------|----------------------|
| Auth      | `/api/v1/auth`       |
| Catalog   | `/api/v1/catalog`    |
| Analytics | `/api/v1/analytics`  |
| Audit     | `/api/v1/audit`      |
| GenAI     | `/api/v1/genai`      |

## Error Format
All errors return structured JSON:
```json
{"detail": "Human-readable message", "code": "machine_readable_code"}
```
""",
    openapi_tags=[
        {"name": "Auth",      "description": "Registration, login (password / OTP / Google OAuth), profile management"},
        {"name": "Catalog",   "description": "User image upload and management"},
        {"name": "Analytics", "description": "Event tracking and aggregated statistics"},
        {"name": "Audit",     "description": "Structured log ingestion and search (admin/debug)"},
        {"name": "GenAI",     "description": "AI-assisted fashion: Style Critique (Ollama/qwen3.5:9b) and apparel generation"},
    ],
)

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

# Serve uploaded/generated images
UPLOAD_DIR = os.environ.get(
    "UPLOAD_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"),
)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Schemas — Auth
# ---------------------------------------------------------------------------

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    model_config = {"json_schema_extra": {"example": {"email": "alice@example.com", "password": "SecurePass123"}}}

    @field_validator("password")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class TokenRefreshBody(BaseModel):
    token: str


class OTPRequestBody(BaseModel):
    email: EmailStr
    model_config = {"json_schema_extra": {"example": {"email": "alice@example.com"}}}


class OTPVerifyBody(BaseModel):
    email: EmailStr
    otp: str
    model_config = {"json_schema_extra": {"example": {"email": "alice@example.com", "otp": "482931"}}}


class GoogleTokenBody(BaseModel):
    id_token: str
    model_config = {"json_schema_extra": {"example": {"id_token": "<Google ID token>"}}}


class UserUpdateBody(BaseModel):
    email: Optional[EmailStr] = None
    model_config = {"json_schema_extra": {"example": {"email": "newemail@example.com"}}}


class RoleUpdateBody(BaseModel):
    role: str
    model_config = {"json_schema_extra": {"example": {"role": "tailor"}}}


# ---------------------------------------------------------------------------
# Schemas — Catalog
# ---------------------------------------------------------------------------

class ImageOut(BaseModel):
    id: int
    user_id: int
    url: str
    image_type: str
    prompt: Optional[str]
    created_at: str


class QuotaOut(BaseModel):
    used: int
    limit: int
    remaining: int


# ---------------------------------------------------------------------------
# Schemas — Analytics
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    service: str
    event_type: str
    user_id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None
    model_config = {"json_schema_extra": {"example": {"service": "frontend", "event_type": "page_view", "user_id": 1}}}


class StatRow(BaseModel):
    event_type: str
    count: int


class UsageStatsOut(BaseModel):
    stats: List[StatRow]


# ---------------------------------------------------------------------------
# Schemas — Audit
# ---------------------------------------------------------------------------

class AuditLogCreate(BaseModel):
    service_name: str
    level: str
    message: str
    payload: Optional[Dict[str, Any]] = None
    model_config = {"json_schema_extra": {"example": {"service_name": "auth", "level": "INFO", "message": "User registered"}}}


class AuditLogOut(BaseModel):
    id: int
    service_name: str
    level: str
    message: str
    payload: Optional[Dict[str, Any]]
    created_at: str


# ---------------------------------------------------------------------------
# Schemas — GenAI
# ---------------------------------------------------------------------------

class GenAIResponse(BaseModel):
    status: str
    message: str


class StyleCritiqueOut(BaseModel):
    critique_id: int
    image_url: str
    markdown: str
    credits_used: int
    credits_remaining: int
    model_used: str
    created_at: Optional[str] = None


class CreditsOut(BaseModel):
    credits: int
    style_critique_cost: int
    image_generation_cost: int


# ---------------------------------------------------------------------------
# Auth + proxy helpers
# ---------------------------------------------------------------------------

_PUBLIC_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/uploads",
)


def _is_public(path: str) -> bool:
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


def _error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "code": code},
    )


def _verify_jwt(request: Request) -> Optional[dict]:
    if _is_public(request.url.path):
        return None
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise _error(401, "Missing or invalid Authorization header. Include 'Bearer <token>'.", "unauthorized")
    token = auth.split(" ", 1)[1]
    try:
        return pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except pyjwt.ExpiredSignatureError:
        raise _error(401, "Your session has expired. Please log in again.", "token_expired")
    except pyjwt.PyJWTError:
        raise _error(401, "Invalid authentication token.", "invalid_token")


async def _forward(request: Request, target_base: str, user: Optional[dict] = None) -> Response:
    target_url = f"{target_base}{request.url.path}"
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    if user:
        headers["x-user-id"] = str(user.get("sub", ""))
        headers["x-user-role"] = str(user.get("role", ""))

    timeout = 300.0 if "/api/v1/genai" in request.url.path else 30.0

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=target_url,
                params=request.query_params,
                headers=headers,
                content=body,
            )
        except httpx.RequestError as exc:
            raise _error(503, f"Service temporarily unavailable. Please try again later.", "service_unavailable")
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


# ---------------------------------------------------------------------------
# Auth router
# ---------------------------------------------------------------------------

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post(
    "/register",
    response_model=TokenOut,
    status_code=201,
    summary="Register a new user",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
async def auth_register(body: RegisterBody, request: Request):
    return await _forward(request, settings.auth_service_url)


@auth_router.post(
    "/login",
    response_model=TokenOut,
    summary="Login with email + password",
    description="Send as `application/x-www-form-urlencoded`. Fields: `username` (email) and `password`.",
    responses={401: {"description": "Incorrect credentials"}},
)
async def auth_login(request: Request):
    return await _forward(request, settings.auth_service_url)


@auth_router.post(
    "/refresh",
    response_model=TokenOut,
    summary="Refresh an expired access token",
    responses={401: {"description": "Invalid token"}},
)
async def auth_refresh(body: TokenRefreshBody, request: Request):
    return await _forward(request, settings.auth_service_url)


@auth_router.post(
    "/login/otp/request",
    summary="Request a 6-digit OTP via email (SMTP)",
    responses={
        200: {"content": {"application/json": {"example": {"detail": "OTP sent to your email address.", "code": "otp_sent"}}}},
        503: {"description": "SMTP not configured"},
    },
)
async def auth_otp_request(body: OTPRequestBody, request: Request):
    return await _forward(request, settings.auth_service_url)


@auth_router.post(
    "/login/otp/verify",
    response_model=TokenOut,
    summary="Verify OTP and receive JWT",
    responses={400: {"description": "Invalid or expired OTP"}},
)
async def auth_otp_verify(body: OTPVerifyBody, request: Request):
    return await _forward(request, settings.auth_service_url)


@auth_router.post(
    "/login/google",
    response_model=TokenOut,
    summary="Login via Google OAuth (ID token)",
    responses={401: {"description": "Invalid Google token"}},
)
async def auth_google(body: GoogleTokenBody, request: Request):
    return await _forward(request, settings.auth_service_url)


@auth_router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile",
    description="Returns the full user object including id, email, role, and created_at.",
    responses={401: {"description": "Unauthorized"}},
)
async def auth_me(request: Request, credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    user = _verify_jwt(request)
    return await _forward(request, settings.auth_service_url, user)


@auth_router.patch(
    "/me",
    response_model=UserOut,
    summary="Update current user profile",
    description="Update mutable profile fields (e.g. email). Returns the updated user.",
    responses={
        409: {"description": "Email already in use"},
        401: {"description": "Unauthorized"},
    },
)
async def auth_update_me(
    body: UserUpdateBody,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.auth_service_url, user)


@auth_router.put(
    "/me/role",
    response_model=UserOut,
    summary="Update current user role",
    description="Allowed values: `user`, `tailor`. Cannot self-assign `admin`.",
    responses={
        400: {"description": "Invalid role"},
        401: {"description": "Unauthorized"},
    },
)
async def auth_update_role(
    body: RoleUpdateBody,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.auth_service_url, user)


# ---------------------------------------------------------------------------
# Catalog router (images only)
# ---------------------------------------------------------------------------

catalog_router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


@catalog_router.post(
    "/images/upload",
    response_model=ImageOut,
    status_code=201,
    summary="Upload a user image (quota enforced)",
    description="Accepts `multipart/form-data`. Allowed types: JPEG, PNG, WebP. Max 5 MB. Daily quota: 20 images/user.",
    responses={
        413: {"description": "File exceeds 5 MB"},
        422: {"description": "Unsupported file type"},
        429: {"description": "Daily quota reached"},
    },
)
async def catalog_image_upload(
    request: Request,
    file: UploadFile = File(..., description="Image file (JPEG / PNG / WebP, max 5 MB)"),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    if not user:
        raise _error(401, "Authentication required.", "unauthorized")

    target_url = f"{settings.catalog_service_url}{request.url.path}"
    file_bytes = await file.read()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-type", "content-length")}
    headers["x-user-id"] = str(user.get("sub", ""))
    headers["x-user-role"] = str(user.get("role", ""))

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                url=target_url,
                params=request.query_params,
                headers=headers,
                files={"file": (file.filename or "image.png", file_bytes, file.content_type)},
            )
        except httpx.RequestError as exc:
            raise _error(503, "Service temporarily unavailable. Please try again later.", "service_unavailable")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@catalog_router.get(
    "/images/quota",
    response_model=QuotaOut,
    summary="Get today's image upload quota usage",
)
async def catalog_image_quota(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.catalog_service_url, user)


@catalog_router.get(
    "/images/me",
    response_model=List[ImageOut],
    summary="Get current user's images (uploaded + generated)",
    description="Returns all images belonging to the authenticated user. Filter by `image_type=upload` or `image_type=generated`.",
)
async def catalog_user_images(
    request: Request,
    image_type: Optional[str] = Query(None, description="Filter by type: upload or generated"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.catalog_service_url, user)


@catalog_router.get(
    "/images/{image_id}",
    response_model=ImageOut,
    summary="Get a single image by ID",
    responses={404: {"description": "Not found or not owned by you"}},
)
async def catalog_get_image(
    image_id: int,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.catalog_service_url, user)


@catalog_router.delete(
    "/images/{image_id}",
    status_code=204,
    summary="Delete an image (owner only)",
    responses={404: {"description": "Not found or not owned by you"}},
)
async def catalog_delete_image(
    image_id: int,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.catalog_service_url, user)


# ---------------------------------------------------------------------------
# Analytics router
# ---------------------------------------------------------------------------

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@analytics_router.post(
    "/track",
    status_code=201,
    summary="Track an event (public — no auth required)",
    description="Fire-and-forget from the frontend.",
    responses={201: {"content": {"application/json": {"example": {"status": "ok", "event_id": 99}}}}},
)
async def analytics_track(body: EventCreate, request: Request):
    return await _forward(request, settings.analytics_service_url)


@analytics_router.get("/stats/usage", summary="Event counts grouped by event_type")
async def analytics_usage(
    request: Request,
    service: Optional[str] = Query(None, description="Filter by service name"),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.analytics_service_url, user)


@analytics_router.get("/stats/daily", summary="Event counts per day for the last N days")
async def analytics_daily(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    service: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.analytics_service_url, user)


@analytics_router.get("/stats/users", summary="Most active users by event count")
async def analytics_users(
    request: Request,
    top: int = Query(10, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.analytics_service_url, user)


@analytics_router.get("/events", summary="Raw event log with filters")
async def analytics_events(
    request: Request,
    service: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.analytics_service_url, user)


# ---------------------------------------------------------------------------
# Audit router
# ---------------------------------------------------------------------------

audit_router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


@audit_router.post(
    "/log",
    status_code=201,
    summary="Ingest a structured log entry (service-to-service, no auth)",
    description="Valid levels: `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`",
    responses={422: {"description": "Invalid level or empty fields"}},
)
async def audit_log(body: AuditLogCreate, request: Request):
    return await _forward(request, settings.audit_service_url)


@audit_router.get(
    "/search",
    response_model=List[AuditLogOut],
    summary="Search audit logs",
    description="All filters are optional and combinable.",
)
async def audit_search(
    request: Request,
    service: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    message_contains: Optional[str] = Query(None),
    since_minutes: Optional[int] = Query(None, ge=1, le=10080),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.audit_service_url, user)


@audit_router.get("/stats", summary="Audit log counts grouped by service + level")
async def audit_stats(
    request: Request,
    days: int = Query(1, ge=1, le=30),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.audit_service_url, user)


@audit_router.get(
    "/logs/{log_id}",
    response_model=AuditLogOut,
    summary="Get a single log entry",
    responses={404: {"description": "Not found"}},
)
async def audit_log_detail(
    log_id: int,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.audit_service_url, user)


@audit_router.delete("/purge", status_code=204, summary="Delete logs older than N days (maintenance)")
async def audit_purge(
    request: Request,
    older_than_days: int = Query(30, ge=1),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.audit_service_url, user)


@audit_router.get("/health", summary="Audit service health check (public)")
async def audit_health(request: Request):
    return await _forward(request, settings.audit_service_url)


# ---------------------------------------------------------------------------
# GenAI router
# ---------------------------------------------------------------------------

genai_router = APIRouter(prefix="/api/v1/genai", tags=["GenAI"])


@genai_router.post(
    "/generate/scratch-or-sketch",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}, "description": "Generated apparel image."}},
    status_code=200,
    summary="Generate high-fashion apparel from a prompt + optional sketch.",
)
async def genai_generate_scratch_or_sketch(
    request: Request,
    positive_prompt: str = Form(...),
    negative_prompt: str = Form("pale fabric, washed out colors, low quality, distorted, blurry"),
    sketch_file: Optional[UploadFile] = File(None),
    target_class: str = Form("long_sleeve_outwear"),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    if not user:
        raise _error(401, "Authentication required.", "unauthorized")

    target_url = f"{settings.genai_service_url}{request.url.path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-type", "content-length")}
    headers["x-user-id"] = str(user.get("sub", ""))
    headers["x-user-role"] = str(user.get("role", ""))

    data = {
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "target_class": target_class,
    }
    files = {}
    if sketch_file:
        file_bytes = await sketch_file.read()
        files["sketch_file"] = (sketch_file.filename or "sketch.png", file_bytes, sketch_file.content_type)

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            resp = await client.post(
                url=target_url,
                params=request.query_params,
                headers=headers,
                data=data,
                files=files if files else None,
            )
        except httpx.RequestError as exc:
            raise _error(503, "Service temporarily unavailable. Please try again later.", "service_unavailable")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "image/png"),
    )


@genai_router.post(
    "/analyze/style-critique",
    response_model=StyleCritiqueOut,
    status_code=200,
    summary="AI Style Critique — upload outfit image, receive structured markdown critique.",
    description=(
        "Sends the image to local Ollama qwen3.5:9b. "
        "Costs **5 credits** per analysis. Requires a valid Bearer token. "
        "The markdown response is saved to the database."
    ),
    responses={
        402: {"description": "Insufficient credits"},
        503: {"description": "Ollama not running or model not pulled"},
        413: {"description": "Image exceeds 5 MB"},
        422: {"description": "Unsupported file type"},
    },
)
async def genai_style_critique(
    request: Request,
    image: UploadFile = File(..., description="Fashion outfit image (JPEG/PNG/WebP, max 5 MB)"),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    """Proxy multipart image upload to genai service for style critique."""
    user = _verify_jwt(request)
    if not user:
        raise _error(401, "Authentication required.", "unauthorized")

    target_url = f"{settings.genai_service_url}/api/v1/genai/analyze/style-critique"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-type", "content-length")}
    headers["x-user-id"] = str(user.get("sub", ""))
    headers["x-user-role"] = str(user.get("role", ""))

    file_bytes = await image.read()
    files = {"image": (image.filename or "outfit.jpg", file_bytes, image.content_type)}

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            resp = await client.post(url=target_url, headers=headers, files=files)
        except httpx.RequestError:
            raise _error(503, "Service temporarily unavailable. Please try again later.", "service_unavailable")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@genai_router.get(
    "/analyze/style-critique/me",
    summary="List my style critiques (paginated)",
)
async def genai_list_critiques(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.genai_service_url, user)


@genai_router.get(
    "/analyze/style-critique/{critique_id}",
    summary="Get a single style critique by ID",
    responses={404: {"description": "Not found or not owned by you"}},
)
async def genai_get_critique(
    critique_id: int,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.genai_service_url, user)


@genai_router.get(
    "/credits",
    response_model=CreditsOut,
    summary="Get current user's credit balance",
)
async def genai_credits(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    user = _verify_jwt(request)
    return await _forward(request, settings.genai_service_url, user)


# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(genai_router)


# ---------------------------------------------------------------------------
# Dynamic Catch-All Router
# ---------------------------------------------------------------------------

def _is_catch_all_public(path: str, method: str) -> bool:
    path = path.lower()
    if path.endswith("/health") or path.endswith("/status"):
        return True
    if any(p in path for p in ["/auth/login", "/auth/register", "/analytics/track"]):
        return True
    return False


@app.api_route(
    "/api/v1/{service}/{rest_of_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def catch_all_gateway(request: Request, service: str, rest_of_path: str):
    service_urls = {
        "auth": settings.auth_service_url,
        "catalog": settings.catalog_service_url,
        "analytics": settings.analytics_service_url,
        "audit": settings.audit_service_url,
        "genai": settings.genai_service_url,
    }

    if service not in service_urls:
        raise _error(404, f"Service '{service}' not found.", "service_not_found")

    target_base = service_urls[service]
    user = None
    if not _is_catch_all_public(request.url.path, request.method):
        user = _verify_jwt(request)

    return await _forward(request, target_base, user)


# ---------------------------------------------------------------------------
# OpenAPI merging
# ---------------------------------------------------------------------------

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
    )

    services = {
        "Auth": settings.auth_service_url,
        "Catalog": settings.catalog_service_url,
        "Analytics": settings.analytics_service_url,
        "Audit": settings.audit_service_url,
        "GenAI": settings.genai_service_url,
    }

    import httpx as sync_httpx
    with sync_httpx.Client(timeout=5.0) as client:
        for service_name, base_url in services.items():
            try:
                resp = client.get(f"{base_url}/openapi.json")
                if resp.status_code == 200:
                    upstream_schema = resp.json()
                    for path, path_item in upstream_schema.get("paths", {}).items():
                        if path not in openapi_schema["paths"]:
                            openapi_schema["paths"][path] = path_item
                        else:
                            for method, operation in path_item.items():
                                original_security = openapi_schema["paths"][path].get(method, {}).get("security")
                                openapi_schema["paths"][path][method] = operation
                                if original_security:
                                    openapi_schema["paths"][path][method]["security"] = original_security
                    if "components" in upstream_schema:
                        openapi_schema.setdefault("components", {})
                        for comp_type, comp_dict in upstream_schema["components"].items():
                            openapi_schema["components"].setdefault(comp_type, {})
                            for comp_key, comp_val in comp_dict.items():
                                openapi_schema["components"][comp_type][comp_key] = comp_val
            except Exception as e:
                print(f"Failed to fetch OpenAPI from {service_name}: {e}")

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


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
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "code": "internal_error"},
    )
