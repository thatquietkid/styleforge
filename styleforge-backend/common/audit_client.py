"""
Shared audit logging client used by all microservices.

fire_audit() is safe to call from both async request handlers and
synchronous contexts (e.g. startup code, background threads).
It never raises and never blocks the caller.
"""
import asyncio
import threading
import httpx
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.config import settings

_AUDIT_URL = f"{settings.audit_service_url}/api/v1/audit/log"


def _build_payload(service_name: str, level: str, message: str, payload: dict | None) -> dict:
    return {
        "service_name": service_name,
        "level": level,
        "message": message,
        "payload": payload or {},
    }


async def send_audit_log(
    service_name: str,
    level: str,
    message: str,
    payload: dict | None = None,
) -> None:
    """Async fire-and-forget HTTP POST to the audit service."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(_AUDIT_URL, json=_build_payload(service_name, level, message, payload))
    except Exception:
        pass  # Never let audit logging crash the caller


def _sync_send(service_name: str, level: str, message: str, payload: dict | None) -> None:
    """Blocking sync HTTP POST — runs in a daemon thread."""
    try:
        httpx.post(_AUDIT_URL, json=_build_payload(service_name, level, message, payload), timeout=3.0)
    except Exception:
        pass


def fire_audit(
    service_name: str,
    level: str,
    message: str,
    payload: dict | None = None,
) -> None:
    """
    Schedule an audit log entry without blocking the caller.

    Works correctly whether called from:
    - An async FastAPI route handler  → schedules a coroutine task
    - A sync context (startup, thread) → spawns a daemon thread
    """
    try:
        loop = asyncio.get_running_loop()
        # We are inside a running event loop — schedule as a task
        loop.create_task(send_audit_log(service_name, level, message, payload))
    except RuntimeError:
        # No running event loop — use a daemon thread so we don't block
        t = threading.Thread(
            target=_sync_send,
            args=(service_name, level, message, payload),
            daemon=True,
        )
        t.start()
