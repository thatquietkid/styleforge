"""
Analytics Microservice
Ingests service events and provides aggregated usage statistics.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.database import get_db
from common.models import AnalyticsEvent
from common.audit_client import fire_audit

app = FastAPI(title="Styleforge Analytics Service", version="1.0.0")

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
# Schemas
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    user_id: Optional[int] = None
    service: str
    event_type: str
    payload: Optional[Dict[str, Any]] = None

class EventResponse(BaseModel):
    id: int
    user_id: Optional[int]
    service: str
    event_type: str
    payload: Optional[Dict[str, Any]]
    timestamp: datetime
    model_config = {"from_attributes": True}

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/analytics/track", status_code=201)
async def track_event(body: EventCreate, db: AsyncSession = Depends(get_db)):
    """Ingest a single analytics event."""
    event = AnalyticsEvent(
        user_id=body.user_id,
        service=body.service,
        event_type=body.event_type,
        payload=body.payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"status": "ok", "event_id": event.id}


@app.get("/api/v1/analytics/stats/usage")
async def usage_stats(
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Event counts grouped by event_type."""
    query = (
        select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.event_type)
        .order_by(func.count(AnalyticsEvent.id).desc())
    )
    if service:
        query = query.where(AnalyticsEvent.service == service)

    result = await db.execute(query)
    rows = result.all()
    return {"stats": [{"event_type": r[0], "count": r[1]} for r in rows]}


@app.get("/api/v1/analytics/stats/daily")
async def daily_stats(
    days: int = Query(default=7, ge=1, le=90),
    service: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Event counts per day for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    query = (
        select(
            func.date(AnalyticsEvent.timestamp).label("day"),
            func.count(AnalyticsEvent.id).label("count"),
        )
        .where(AnalyticsEvent.timestamp >= since)
        .group_by(func.date(AnalyticsEvent.timestamp))
        .order_by(func.date(AnalyticsEvent.timestamp))
    )
    if service:
        query = query.where(AnalyticsEvent.service == service)

    result = await db.execute(query)
    rows = result.all()
    return {"stats": [{"day": str(r[0]), "count": r[1]} for r in rows]}


@app.get("/api/v1/analytics/stats/users")
async def user_activity(
    top: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Most active users by event count."""
    query = (
        select(AnalyticsEvent.user_id, func.count(AnalyticsEvent.id).label("events"))
        .where(AnalyticsEvent.user_id.isnot(None))
        .group_by(AnalyticsEvent.user_id)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(top)
    )
    result = await db.execute(query)
    rows = result.all()
    return {"stats": [{"user_id": r[0], "events": r[1]} for r in rows]}


@app.get("/api/v1/analytics/events", response_model=List[EventResponse])
async def list_events(
    service: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Raw event log with optional filters."""
    query = select(AnalyticsEvent).order_by(AnalyticsEvent.timestamp.desc()).offset(skip).limit(limit)
    if service:
        query = query.where(AnalyticsEvent.service == service)
    if event_type:
        query = query.where(AnalyticsEvent.event_type == event_type)
    if user_id:
        query = query.where(AnalyticsEvent.user_id == user_id)

    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global(request: Request, exc: Exception):
    fire_audit("analytics", "ERROR", str(exc), {"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
