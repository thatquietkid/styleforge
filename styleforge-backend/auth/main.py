"""
Auth Microservice
Handles user registration, JWT login, OTP (real SMTP), Google OAuth token verification.
"""
import random
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosmtplib
import jwt as pyjwt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import settings
from common.database import get_db
from common.models import User, RoleEnum, OTPRecord
from common.audit_client import fire_audit

app = FastAPI(title="Styleforge Auth Service", version="1.0.0")

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

_ph = PasswordHasher()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

    @field_validator("otp")
    @classmethod
    def otp_format(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be a 6-digit number")
        return v


class GoogleTokenRequest(BaseModel):
    id_token: str


class TokenRefreshRequest(BaseModel):
    token: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

    model_config = {"json_schema_extra": {"example": {"email": "newemail@example.com"}}}


class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        allowed = {r.value for r in RoleEnum if r != RoleEnum.admin}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return _ph.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def _create_jwt(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _token_response(user: User) -> dict:
    return {
        "access_token": _create_jwt(user.id, user.role.value),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "created_at": user.created_at,
        },
    }


def _error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "code": code},
    )


async def _send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP via SMTP using aiosmtplib."""
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_pass:
        raise _error(
            503,
            "Email service is not configured. Please contact support.",
            "smtp_not_configured",
        )

    sender = settings.smtp_from or settings.smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Styleforge Login OTP"
    msg["From"] = f"Styleforge <{sender}>"
    msg["To"] = to_email

    text_body = f"Your Styleforge OTP is: {otp}\n\nThis code expires in 10 minutes. Do not share it."
    html_body = f"""
    <html><body style="font-family:sans-serif;background:#0f0f0f;color:#fff;padding:32px;">
      <div style="max-width:480px;margin:auto;background:#1a1a1a;border-radius:12px;padding:32px;">
        <h2 style="color:#a78bfa">Styleforge Login Code</h2>
        <p>Use this one-time code to log in:</p>
        <div style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#a78bfa;margin:24px 0;">{otp}</div>
        <p style="color:#aaa;font-size:13px;">This code expires in <strong>10 minutes</strong>. Do not share it with anyone.</p>
      </div>
    </body></html>
    """
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            start_tls=True,
        )
    except aiosmtplib.SMTPException as exc:
        raise _error(503, f"Failed to send OTP email: {str(exc)}", "smtp_error")
    except Exception as exc:
        raise _error(503, "Failed to send OTP email. Please try again later.", "smtp_error")


# ---------------------------------------------------------------------------
# Validation error handler
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user with email + password."""
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise _error(409, "An account with this email already exists.", "email_conflict")

    user = User(
        email=body.email,
        hashed_password=_hash_password(body.password),
        role=RoleEnum.user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    fire_audit("auth", "INFO", "User registered", {"user_id": user.id, "email": user.email})
    return _token_response(user)


@app.post("/api/v1/auth/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login with email (username field) + password."""
    result = await db.execute(select(User).where(User.email == form.username))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.hashed_password or not _verify_password(form.password, user.hashed_password):
        fire_audit("auth", "WARN", "Failed login attempt", {"email": form.username})
        raise _error(401, "Incorrect email or password.", "invalid_credentials")

    fire_audit("auth", "INFO", "User logged in", {"user_id": user.id})
    return _token_response(user)


@app.post("/api/v1/auth/login/otp/request")
async def request_otp(body: OTPRequest, db: AsyncSession = Depends(get_db)):
    """Send a 6-digit OTP to the user's email via SMTP."""
    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Invalidate any existing unused OTPs for this email
    await db.execute(
        delete(OTPRecord).where(OTPRecord.email == body.email, OTPRecord.used == False)
    )

    # Store hashed OTP in DB
    otp_record = OTPRecord(
        email=body.email,
        otp_hash=_ph.hash(otp),
        expires_at=expires_at,
        used=False,
    )
    db.add(otp_record)
    await db.commit()

    # Send via real SMTP (Strictly Prod, no dev fallback)
    await _send_otp_email(body.email, otp)

    fire_audit("auth", "INFO", "OTP requested", {"email": body.email})
    return {"detail": "OTP sent to your email address.", "code": "otp_sent"}


@app.post("/api/v1/auth/login/otp/verify", response_model=Token)
async def verify_otp(body: OTPVerify, db: AsyncSession = Depends(get_db)):
    """Verify OTP and return JWT. Creates account on first use."""
    now = datetime.now(timezone.utc)

    # Fetch the most recent unused OTP for this email
    result = await db.execute(
        select(OTPRecord)
        .where(
            OTPRecord.email == body.email,
            OTPRecord.used == False,
            OTPRecord.expires_at > now,
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(1)
    )
    otp_record: OTPRecord | None = result.scalar_one_or_none()

    if not otp_record:
        raise _error(400, "OTP not found or has expired. Please request a new one.", "otp_expired")

    try:
        valid = _ph.verify(otp_record.otp_hash, body.otp)
    except Exception:
        valid = False

    if not valid:
        fire_audit("auth", "WARN", "Invalid OTP attempt", {"email": body.email})
        raise _error(400, "Invalid OTP. Please check the code and try again.", "otp_invalid")

    # Mark as used
    otp_record.used = True
    await db.commit()

    # Get or create user
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()
    if not user:
        user = User(email=body.email, role=RoleEnum.user)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    fire_audit("auth", "INFO", "OTP login success", {"user_id": user.id})
    return _token_response(user)


@app.post("/api/v1/auth/login/google", response_model=Token)
async def google_login(body: GoogleTokenRequest, db: AsyncSession = Depends(get_db)):
    """Verify Google ID token and issue Styleforge JWT."""
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
        google_sub = id_info["sub"]
        email = id_info["email"]
    except Exception as exc:
        raise _error(401, "Invalid or expired Google token.", "invalid_google_token")

    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user: User | None = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_sub = google_sub
        else:
            user = User(email=email, google_sub=google_sub, role=RoleEnum.user)
            db.add(user)

        await db.commit()
        await db.refresh(user)

    fire_audit("auth", "INFO", "Google login", {"user_id": user.id})
    return _token_response(user)


@app.post("/api/v1/auth/refresh", response_model=Token)
async def refresh_token(body: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh an expired signature-valid JWT access token.
    Decodes the token without checking expiration, verifies signature,
    and returns a fresh JWT access token for the user.
    """
    try:
        # Decode without expiration check, but signature check is still active!
        payload = pyjwt.decode(
            body.token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False}
        )
        user_id = int(payload.get("sub", ""))
    except Exception:
        raise _error(401, "Invalid token or signature verification failed.", "invalid_token")

    # Fetch user from database to make sure they still exist
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise _error(404, "User not found.", "user_not_found")

    fire_audit("auth", "INFO", "Token refreshed", {"user_id": user.id})
    return _token_response(user)


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    """Return the currently authenticated user profile."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    try:
        uid = int(user_id)
    except ValueError:
        raise _error(401, "Invalid authentication token.", "unauthorized")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise _error(404, "User not found.", "user_not_found")

    fire_audit("auth", "INFO", "Profile fetched", {"user_id": uid})
    return user


@app.patch("/api/v1/auth/me", response_model=UserResponse)
async def update_me(body: UserUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    """Update the current user's profile fields."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    try:
        uid = int(user_id)
    except ValueError:
        raise _error(401, "Invalid authentication token.", "unauthorized")

    result = await db.execute(select(User).where(User.id == uid))
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise _error(404, "User not found.", "user_not_found")

    if body.email and body.email != user.email:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise _error(409, "This email is already in use.", "email_conflict")
        user.email = body.email

    await db.commit()
    await db.refresh(user)
    fire_audit("auth", "INFO", "Profile updated", {"user_id": uid})
    return user


@app.put("/api/v1/auth/me/role", response_model=UserResponse)
async def update_role(body: RoleUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    """Update current user's role. Allowed values: user, tailor."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise _error(401, "Authentication required.", "unauthorized")

    try:
        uid = int(user_id)
    except ValueError:
        raise _error(401, "Invalid authentication token.", "unauthorized")

    result = await db.execute(select(User).where(User.id == uid))
    user: User | None = result.scalar_one_or_none()
    if not user:
        raise _error(404, "User not found.", "user_not_found")

    user.role = RoleEnum(body.role)
    await db.commit()
    await db.refresh(user)
    fire_audit("auth", "INFO", "User role updated", {"user_id": user.id, "new_role": body.role})
    return user


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/v1/auth/health")
async def health():
    return {"status": "ok", "service": "auth"}


# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": str(detail), "code": "error"})


@app.exception_handler(Exception)
async def _global(request: Request, exc: Exception):
    fire_audit("auth", "ERROR", str(exc), {"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "code": "internal_error"},
    )
