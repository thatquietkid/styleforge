"""
Audit Microservice
Central structured log store for all microservices.
Accepts async fire-and-forget POST logs and provides search/filter/stats APIs.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.database import get_db
from common.models import AuditLog

app = FastAPI(title="Styleforge Audit Service", version="1.0.0")

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

VALID_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AuditLogCreate(BaseModel):
    service_name: str
    level: str
    message: str
    payload: Optional[dict] = None

    @field_validator("level")
    @classmethod
    def valid_level(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_LEVELS:
            raise ValueError(f"level must be one of {VALID_LEVELS}")
        return v

    @field_validator("service_name", "message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

class AuditLogResponse(BaseModel):
    id: int
    service_name: str
    level: str
    message: str
    payload: Optional[dict]
    created_at: datetime
    model_config = {"from_attributes": True}

class AuditStats(BaseModel):
    service_name: str
    level: str
    count: int

# ---------------------------------------------------------------------------
# Incoming – receive log entries
# ---------------------------------------------------------------------------

@app.post("/api/v1/audit/log", status_code=201)
async def receive_log(body: AuditLogCreate, db: AsyncSession = Depends(get_db)):
    """Accept a structured log entry from any microservice."""
    log = AuditLog(
        service_name=body.service_name,
        level=body.level,
        message=body.message,
        payload=body.payload,
    )
    db.add(log)
    await db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Outgoing – query / search log entries
# ---------------------------------------------------------------------------

@app.get("/api/v1/audit/search", response_model=List[AuditLogResponse])
async def search_logs(
    service: Optional[str] = None,
    level: Optional[str] = None,
    message_contains: Optional[str] = None,
    since_minutes: Optional[int] = Query(default=None, ge=1, le=10080),  # max 7 days
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Search audit logs with optional filters.
    - `service`: exact service name match
    - `level`: log level (INFO, WARN, ERROR, etc.)
    - `message_contains`: substring match on message
    - `since_minutes`: only return logs from the last N minutes
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    filters = []
    if service:
        filters.append(AuditLog.service_name == service)
    if level:
        filters.append(AuditLog.level == level.upper())
    if message_contains:
        filters.append(AuditLog.message.ilike(f"%{message_contains}%"))
    if since_minutes:
        since = datetime.utcnow() - timedelta(minutes=since_minutes)
        filters.append(AuditLog.created_at >= since)

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/v1/audit/stats")
async def audit_stats(
    days: int = Query(default=1, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Return count of log entries grouped by service and level for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(
            AuditLog.service_name,
            AuditLog.level,
            func.count(AuditLog.id).label("count"),
        )
        .where(AuditLog.created_at >= since)
        .group_by(AuditLog.service_name, AuditLog.level)
        .order_by(func.count(AuditLog.id).desc())
    )
    rows = result.all()
    return {
        "period_days": days,
        "stats": [{"service": r[0], "level": r[1], "count": r[2]} for r in rows],
    }


@app.get("/api/v1/audit/logs/{log_id}", response_model=AuditLogResponse)
async def get_log(log_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a single audit log entry by ID."""
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return log


@app.delete("/api/v1/audit/purge", status_code=204)
async def purge_old_logs(
    older_than_days: int = Query(default=30, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Delete log entries older than N days (retention cleanup)."""
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    result = await db.execute(select(AuditLog).where(AuditLog.created_at < cutoff))
    logs = result.scalars().all()
    for log in logs:
        await db.delete(log)
    await db.commit()


# ---------------------------------------------------------------------------
# Health check (no auth needed)
# ---------------------------------------------------------------------------

@app.get("/api/v1/audit/health")
async def health():
    return {"status": "ok", "service": "audit"}


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global(request: Request, exc: Exception):
    # NOTE: We do NOT call fire_audit here – that would cause infinite recursion
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
