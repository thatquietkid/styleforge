"""
Tests for the GenAI microservice — Style Critique & Scratch Generation.

Test classification:
  [PASS]  Tests that are expected to pass under normal mocked conditions.
  [FAIL]  Tests intentionally written to expose known system limitations,
          race conditions, or strict assertions the implementation cannot
          always guarantee. These failures are documented for the
          dissertation report as evidence of system boundary conditions.

Run with:
    pytest tests/test_genai.py -v --tb=short
"""
import io
import os
import sys
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("POSTGRES_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("DAILY_IMAGE_QUOTA", "5")

from common.database import Base, get_db
from common import models  # noqa: registers all ORM tables
from common.models import User, RoleEnum, StyleCritique, CreditTransaction
from genai.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def genai_client(db_engine):
    """AsyncClient wired to the genai FastAPI app with an in-memory SQLite DB."""
    import common.database as db_mod
    db_mod.engine = db_engine
    db_mod.async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with db_mod.async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


import uuid

async def _create_user(db: AsyncSession, credits: int = 100) -> User:
    """Helper: insert a user with a given credit balance."""
    user = User(email=f"test_{uuid.uuid4().hex}@styleforge.ai", role=RoleEnum.user, credits=credits)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _fake_image_bytes() -> bytes:
    """Return minimal valid JPEG bytes (1×1 white pixel) for upload tests."""
    from PIL import Image as PILImage
    buf = io.BytesIO()
    PILImage.new("RGB", (100, 100), color=(200, 200, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _make_file_upload(content: bytes = None, content_type: str = "image/jpeg", filename: str = "outfit.jpg"):
    return ("image", (filename, content or _fake_image_bytes(), content_type))


# ---------------------------------------------------------------------------
# [PASS] Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_genai_health(genai_client):
    """[PASS] Health endpoint returns service name and ok status."""
    resp = await genai_client.get("/api/v1/genai/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "genai"


# ---------------------------------------------------------------------------
# [PASS] Credits endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_credits_success(genai_client, db_session):
    """[PASS] Authenticated user can retrieve their credit balance."""
    user = await _create_user(db_session, credits=75)

    resp = await genai_client.get(
        "/api/v1/genai/credits",
        headers={"x-user-id": str(user.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["credits"] == 75
    assert "style_critique_cost" in body
    assert "image_generation_cost" in body


@pytest.mark.asyncio
async def test_get_credits_no_auth(genai_client):
    """[PASS] Missing x-user-id header returns 401."""
    resp = await genai_client.get("/api/v1/genai/credits")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# [PASS] Style Critique — sunny day
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("genai.main._preflight_ollama", new_callable=AsyncMock)
@patch("genai.main._call_ollama_critique", new_callable=AsyncMock)
async def test_style_critique_success(mock_ollama, mock_preflight, genai_client, db_session):
    """
    [PASS] Sunny day: valid image, enough credits, Ollama mocked to return
    structured markdown. Verifies response body, credit deduction, and DB record.
    """
    mock_preflight.return_value = None
    mock_ollama.return_value = (
        "### 1. The Core Issue\n- The trousers are too baggy.\n\n"
        "### 2. Aesthetic Breakdown (Garment Critique)\n"
        "- **Color Harmony:** Clashes between navy and brown.\n"
        "- **Fit & Silhouette:** Boxy silhouette loses shape.\n"
        "- **Sartorial Styling & Textures:** Mixed casual/formal cues.\n"
        "- **Model Posture & Presentation:** Slouched shoulders reduce impact.\n\n"
        "### 3. Execution Plan (Actionable Fixes)\n"
        "- **The Garment Swap:** Replace trousers with slim-cut chinos.\n"
        "- **The Tailoring/Fit Adjustment:** Taper at the ankle.\n"
        "- **The Accessory/Footwear Refinement:** Switch to leather loafers."
    )

    user = await _create_user(db_session, credits=50)
    img_bytes = _fake_image_bytes()

    with patch("genai.main.aiofiles.open", create=True) as mock_aio:
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(write=AsyncMock()))
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = await genai_client.post(
            "/api/v1/genai/analyze/style-critique",
            headers={"x-user-id": str(user.id)},
            files=[_make_file_upload(img_bytes)],
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "markdown" in body
    assert "### 1. The Core Issue" in body["markdown"]
    assert body["credits_used"] == 5
    assert body["credits_remaining"] == 45
    assert body["model_used"] == "qwen3.5:9b"
    assert "critique_id" in body

    # Verify DB record was created
    from sqlalchemy import select
    result = await db_session.execute(
        select(StyleCritique).where(StyleCritique.user_id == user.id)
    )
    critique = result.scalar_one_or_none()
    assert critique is not None
    assert "The Core Issue" in critique.markdown_response

    # Verify credit transaction logged
    tx_result = await db_session.execute(
        select(CreditTransaction).where(CreditTransaction.user_id == user.id)
    )
    tx = tx_result.scalar_one_or_none()
    assert tx is not None
    assert tx.amount == -5
    assert tx.balance_after == 45


# ---------------------------------------------------------------------------
# [PASS] Style Critique — edge cases that should be handled gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_style_critique_no_auth(genai_client):
    """[PASS] Request with no x-user-id header returns 401 Unauthorized."""
    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        files=[_make_file_upload()],
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_style_critique_invalid_file_type(genai_client, db_session):
    """[PASS] Uploading a PDF file returns 422 with invalid_file_type code."""
    user = await _create_user(db_session, credits=100)
    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        headers={"x-user-id": str(user.id)},
        files=[("image", ("document.pdf", b"%PDF-1.4 fake content", "application/pdf"))],
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "invalid_file_type"


@pytest.mark.asyncio
async def test_style_critique_file_too_large(genai_client, db_session):
    """[PASS] A file exceeding 5 MB returns 413 with file_too_large code."""
    user = await _create_user(db_session, credits=100)
    large_bytes = b"x" * (5 * 1024 * 1024 + 1)
    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        headers={"x-user-id": str(user.id)},
        files=[("image", ("big.jpg", large_bytes, "image/jpeg"))],
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "file_too_large"


@pytest.mark.asyncio
async def test_style_critique_empty_file(genai_client, db_session):
    """[PASS] An empty file body returns 422 with empty_file code."""
    user = await _create_user(db_session, credits=100)
    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        headers={"x-user-id": str(user.id)},
        files=[("image", ("empty.jpg", b"", "image/jpeg"))],
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "empty_file"


@pytest.mark.asyncio
async def test_style_critique_insufficient_credits(genai_client, db_session):
    """
    [PASS] A user with 0 credits receives a 402 Payment Required response
    with code 'insufficient_credits' before Ollama is ever contacted.
    """
    user = await _create_user(db_session, credits=0)
    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        headers={"x-user-id": str(user.id)},
        files=[_make_file_upload()],
    )
    assert resp.status_code == 402
    assert resp.json()["code"] == "insufficient_credits"
    assert "have 0" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_style_critique_exactly_enough_credits(genai_client, db_session):
    """
    [PASS] A user with exactly 5 credits (the cost) can still run a critique.
    After the call, their balance should be exactly 0.
    """
    from common.config import settings as _settings

    mock_text = "### 1. The Core Issue\n- Minimal critique."

    with (
        patch("genai.main._preflight_ollama", new_callable=AsyncMock) as mock_pre,
        patch("genai.main._call_ollama_critique", new_callable=AsyncMock) as mock_call,
        patch("genai.main.aiofiles.open", create=True) as mock_aio,
    ):
        mock_pre.return_value = None
        mock_call.return_value = mock_text
        mock_aio.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(write=AsyncMock()))
        mock_aio.return_value.__aexit__ = AsyncMock(return_value=False)

        user = await _create_user(db_session, credits=_settings.style_critique_credits)

        resp = await genai_client.post(
            "/api/v1/genai/analyze/style-critique",
            headers={"x-user-id": str(user.id)},
            files=[_make_file_upload()],
        )

    assert resp.status_code == 200
    assert resp.json()["credits_remaining"] == 0


@pytest.mark.asyncio
@patch("genai.main._preflight_ollama", new_callable=AsyncMock)
async def test_style_critique_ollama_unavailable(mock_preflight, genai_client, db_session):
    """
    [PASS] When Ollama daemon is not running, the preflight check raises 503
    with code 'ollama_unavailable' before any credits are deducted.
    """
    from fastapi import HTTPException
    mock_preflight.side_effect = HTTPException(
        status_code=503,
        detail={"detail": "Ollama is not running.", "code": "ollama_unavailable"},
    )
    user = await _create_user(db_session, credits=50)

    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        headers={"x-user-id": str(user.id)},
        files=[_make_file_upload()],
    )
    assert resp.status_code == 503
    assert resp.json()["code"] == "ollama_unavailable"

    # Critically: verify credits were NOT deducted
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.id == user.id))
    refreshed = result.scalar_one()
    assert refreshed.credits == 50, "Credits must NOT be deducted when Ollama fails preflight"


@pytest.mark.asyncio
@patch("genai.main._preflight_ollama", new_callable=AsyncMock)
@patch("genai.main._call_ollama_critique", new_callable=AsyncMock)
async def test_style_critique_ollama_model_missing(mock_call, mock_pre, genai_client, db_session):
    """
    [PASS] When the qwen3.5:9b model is not pulled, the preflight returns 503
    with code 'ollama_model_missing'.
    """
    from fastapi import HTTPException
    mock_pre.side_effect = HTTPException(
        status_code=503,
        detail={"detail": "Model not pulled.", "code": "ollama_model_missing"},
    )
    user = await _create_user(db_session, credits=50)

    resp = await genai_client.post(
        "/api/v1/genai/analyze/style-critique",
        headers={"x-user-id": str(user.id)},
        files=[_make_file_upload()],
    )
    assert resp.status_code == 503
    assert resp.json()["code"] == "ollama_model_missing"


# ---------------------------------------------------------------------------
# [PASS] Critique retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_critique_by_id_success(genai_client, db_session):
    """[PASS] Owner can retrieve their own critique by ID."""
    user = await _create_user(db_session, credits=100)
    critique = StyleCritique(
        user_id=user.id,
        image_path="/uploads/test.jpg",
        markdown_response="### 1. The Core Issue\n- Good basics, poor finishing.",
        credits_used=5,
        model_used="qwen3.5:9b",
    )
    db_session.add(critique)
    await db_session.commit()
    await db_session.refresh(critique)

    resp = await genai_client.get(
        f"/api/v1/genai/analyze/style-critique/{critique.id}",
        headers={"x-user-id": str(user.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["critique_id"] == critique.id
    assert "Core Issue" in body["markdown"]


@pytest.mark.asyncio
async def test_get_critique_not_found(genai_client, db_session):
    """[PASS] Fetching a non-existent critique ID returns 404 not_found."""
    user = await _create_user(db_session)
    resp = await genai_client.get(
        "/api/v1/genai/analyze/style-critique/99999",
        headers={"x-user-id": str(user.id)},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_get_critique_wrong_owner(genai_client, db_session):
    """
    [PASS] User B cannot access User A's critique — returns 404, preventing
    information leakage about other users' analyses.
    """
    user_a = await _create_user(db_session, credits=100)
    user_b = await _create_user(db_session, credits=100)

    critique = StyleCritique(
        user_id=user_a.id,
        image_path="/uploads/private.jpg",
        markdown_response="### Private critique",
        credits_used=5,
        model_used="qwen3.5:9b",
    )
    db_session.add(critique)
    await db_session.commit()
    await db_session.refresh(critique)

    resp = await genai_client.get(
        f"/api/v1/genai/analyze/style-critique/{critique.id}",
        headers={"x-user-id": str(user_b.id)},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_my_critiques(genai_client, db_session):
    """[PASS] User can list all their own critiques, ordered newest first."""
    user = await _create_user(db_session)
    for i in range(3):
        c = StyleCritique(
            user_id=user.id,
            image_path=f"/uploads/img{i}.jpg",
            markdown_response=f"### Critique {i}",
            credits_used=5,
            model_used="qwen3.5:9b",
        )
        db_session.add(c)
    await db_session.commit()

    resp = await genai_client.get(
        "/api/v1/genai/analyze/style-critique/me",
        headers={"x-user-id": str(user.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3


@pytest.mark.asyncio
async def test_list_my_critiques_empty(genai_client, db_session):
    """[PASS] A new user with no critiques gets an empty list, not an error."""
    user = await _create_user(db_session)
    resp = await genai_client.get(
        "/api/v1/genai/analyze/style-critique/me",
        headers={"x-user-id": str(user.id)},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# [PASS] Scratch/sketch generation — credit enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scratch_generation_insufficient_credits(genai_client, db_session):
    """
    [PASS] A user with only 3 credits (need 10 for generation) receives 402
    before the Colab backend is contacted.
    """
    user = await _create_user(db_session, credits=3)
    img_bytes = _fake_image_bytes()

    resp = await genai_client.post(
        "/api/v1/genai/generate/scratch-or-sketch",
        headers={"x-user-id": str(user.id)},
        data={
            "positive_prompt": "elegant black dress",
            "target_class": "long_sleeve_outwear",
        },
        files=[("sketch_file", ("sketch.jpg", img_bytes, "image/jpeg"))],
    )
    assert resp.status_code == 402
    assert resp.json()["code"] == "insufficient_credits"


@pytest.mark.asyncio
@patch("genai.main.httpx.AsyncClient")
async def test_scratch_generation_backend_unavailable(mock_client_cls, genai_client, db_session):
    """
    [PASS] When the Colab backend health check fails (connection refused),
    the endpoint returns 503 with backend_unavailable code.
    """
    import httpx as real_httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=real_httpx.RequestError("Connection refused"))
    mock_client_cls.return_value = mock_client

    user = await _create_user(db_session, credits=100)
    img_bytes = _fake_image_bytes()

    resp = await genai_client.post(
        "/api/v1/genai/generate/scratch-or-sketch",
        headers={"x-user-id": str(user.id)},
        data={"positive_prompt": "stylish blazer", "target_class": "long_sleeve_outwear"},
        files=[("sketch_file", ("sketch.jpg", img_bytes, "image/jpeg"))],
    )
    assert resp.status_code == 503
    assert resp.json()["code"] == "backend_unavailable"


# ===========================================================================
# INTENTIONAL FAILURES — Documented for dissertation
# These tests expose known system limitations. They are expected to FAIL.
# ===========================================================================

@pytest.mark.asyncio
async def test_FAIL_critique_response_always_has_three_sections(genai_client, db_session):
    """
    [FAIL — KNOWN LIMITATION] This test asserts that the Ollama model's
    markdown response ALWAYS contains all three required sections.

    DISSERTATION NOTE: Language models are probabilistic. qwen3.5:9b may
    occasionally omit a section, merge sections, or deviate from the prompt
    structure. This test demonstrates that the system has NO structural
    validation on the model's output — it stores and returns whatever the
    model produces, even if malformed. A production system would require
    output parsing/validation. This test is EXPECTED TO FAIL when the mock
    returns an incomplete response, demonstrating this gap.
    """
    # Simulate an incomplete model response (only 2 of 3 sections)
    incomplete_response = (
        "### 1. The Core Issue\n- The outfit lacks cohesion.\n\n"
        "### 2. Aesthetic Breakdown (Garment Critique)\n"
        "- **Color Harmony:** Mixed signals between tones."
        # MISSING: Section 3 — Execution Plan
    )

    with (
        patch("genai.main._preflight_ollama", new_callable=AsyncMock) as mp,
        patch("genai.main._call_ollama_critique", new_callable=AsyncMock) as mc,
        patch("genai.main.aiofiles.open", create=True) as mf,
    ):
        mp.return_value = None
        mc.return_value = incomplete_response
        mf.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(write=AsyncMock()))
        mf.return_value.__aexit__ = AsyncMock(return_value=False)

        user = await _create_user(db_session, credits=50)
        resp = await genai_client.post(
            "/api/v1/genai/analyze/style-critique",
            headers={"x-user-id": str(user.id)},
            files=[_make_file_upload()],
        )

    assert resp.status_code == 200
    markdown = resp.json()["markdown"]

    # This assertion WILL FAIL — the system does NOT validate section completeness
    assert "### 3. Execution Plan" in markdown, (
        "DISSERTATION FAILURE: The backend accepted and stored an incomplete model "
        "response missing Section 3. The system lacks output structure validation."
    )


@pytest.mark.asyncio
async def test_FAIL_credits_cannot_go_negative_concurrent(genai_client, db_session):
    """
    [FAIL — RACE CONDITION] This test simulates a concurrent double-spend by
    making two simultaneous critique requests with a user who has exactly 5 credits.

    DISSERTATION NOTE: The credit deduction in _check_and_deduct_credits() is
    NOT protected by a database-level lock (SELECT FOR UPDATE). In a concurrent
    scenario, two requests can both read credits=5, both pass the check, and both
    deduct 5, leaving the balance at -5. This test is designed to FAIL to
    demonstrate this race condition vulnerability.

    A production fix would require:
      - SELECT FOR UPDATE on the user row, or
      - Optimistic concurrency with a version/etag column, or
      - A Redis-based atomic credit counter.
    """
    import asyncio

    with (
        patch("genai.main._preflight_ollama", new_callable=AsyncMock) as mp,
        patch("genai.main._call_ollama_critique", new_callable=AsyncMock) as mc,
        patch("genai.main.aiofiles.open", create=True) as mf,
    ):
        mp.return_value = None
        mc.return_value = "### 1. The Core Issue\n- Concurrent test."
        mf.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(write=AsyncMock()))
        mf.return_value.__aexit__ = AsyncMock(return_value=False)

        user = await _create_user(db_session, credits=5)  # Just enough for ONE call

        # Fire two requests "simultaneously"
        tasks = await asyncio.gather(
            genai_client.post(
                "/api/v1/genai/analyze/style-critique",
                headers={"x-user-id": str(user.id)},
                files=[_make_file_upload()],
            ),
            genai_client.post(
                "/api/v1/genai/analyze/style-critique",
                headers={"x-user-id": str(user.id)},
                files=[_make_file_upload()],
            ),
            return_exceptions=True,
        )
        responses = [t for t in tasks if not isinstance(t, Exception)]

    # EXPECTED SYSTEM BEHAVIOUR (ideal): exactly one 200 and one 402
    success_count = sum(1 for r in responses if r.status_code == 200)
    blocked_count = sum(1 for r in responses if r.status_code == 402)

    # This assertion WILL FAIL — both requests may succeed due to the race condition
    assert success_count == 1 and blocked_count == 1, (
        f"DISSERTATION FAILURE: Race condition detected. "
        f"{success_count} request(s) succeeded and {blocked_count} were blocked. "
        f"Expected exactly 1 success and 1 block. "
        f"Credits may have gone negative due to missing SELECT FOR UPDATE lock."
    )


@pytest.mark.asyncio
async def test_FAIL_critique_persisted_even_on_partial_db_error(genai_client, db_session):
    """
    [FAIL — ATOMICITY LIMITATION] This test asserts that if saving the critique
    to the DB fails AFTER credits were deducted, the transaction is rolled back
    and credits are restored.

    DISSERTATION NOTE: The current implementation deducts credits and saves the
    critique in a single commit() call, but if an error occurs between adding
    objects to the session and the commit, there is no explicit rollback/compensation
    for the credit deduction. This test demonstrates that error recovery is
    incomplete. This test is EXPECTED TO FAIL because the system does not have
    compensating transactions.
    """
    from sqlalchemy.exc import SQLAlchemyError

    with (
        patch("genai.main._preflight_ollama", new_callable=AsyncMock) as mp,
        patch("genai.main._call_ollama_critique", new_callable=AsyncMock) as mc,
        patch("genai.main.aiofiles.open", create=True) as mf,
    ):
        mp.return_value = None
        mc.return_value = "### 1. The Core Issue\n- DB error test."
        mf.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(write=AsyncMock()))
        mf.return_value.__aexit__ = AsyncMock(return_value=False)

        user = await _create_user(db_session, credits=50)
        original_credits = user.credits

        # Patch db.commit to fail on the FIRST call (after credits deducted, before saved)
        original_commit = db_session.commit
        call_count = 0

        async def patched_commit():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise SQLAlchemyError("Simulated DB failure during commit")
            return await original_commit()

        db_session.commit = patched_commit

        resp = await genai_client.post(
            "/api/v1/genai/analyze/style-critique",
            headers={"x-user-id": str(user.id)},
            files=[_make_file_upload()],
        )

    # Refresh user from DB to see actual credit state
    from sqlalchemy import select as sa_select
    result = await db_session.execute(sa_select(User).where(User.id == user.id))
    refreshed_user = result.scalar_one()

    # This assertion WILL FAIL — credits may have been deducted even though the
    # critique wasn't saved, demonstrating incomplete atomicity
    assert refreshed_user.credits == original_credits, (
        f"DISSERTATION FAILURE: Credits were deducted (from {original_credits} to "
        f"{refreshed_user.credits}) even though the DB commit failed. "
        f"The system lacks compensating transaction logic."
    )


@pytest.mark.asyncio
async def test_FAIL_style_critique_validates_markdown_structure(genai_client, db_session):
    """
    [FAIL — MISSING VALIDATION] This test asserts that the API rejects a
    response from Ollama that is plain text (not markdown with required headers).

    DISSERTATION NOTE: The backend performs NO structural validation on Ollama's
    output. Any non-empty string is accepted and stored. This means:
      - Plain text responses are stored as 'markdown'
      - Hallucinated content is not detected
      - Section headers may be missing or wrongly formatted
    This test FAILS because validation is absent, demonstrating a quality
    assurance gap suitable for a limitations chapter.
    """
    plain_text_response = (
        "The outfit looks quite casual. The jeans fit well but the shoes "
        "don't match the top. Consider changing the footwear."
        # This is plain text — no markdown structure at all
    )

    with (
        patch("genai.main._preflight_ollama", new_callable=AsyncMock) as mp,
        patch("genai.main._call_ollama_critique", new_callable=AsyncMock) as mc,
        patch("genai.main.aiofiles.open", create=True) as mf,
    ):
        mp.return_value = None
        mc.return_value = plain_text_response
        mf.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(write=AsyncMock()))
        mf.return_value.__aexit__ = AsyncMock(return_value=False)

        user = await _create_user(db_session, credits=50)
        resp = await genai_client.post(
            "/api/v1/genai/analyze/style-critique",
            headers={"x-user-id": str(user.id)},
            files=[_make_file_upload()],
        )

    # System SHOULD reject unstructured responses, but it DOES NOT.
    # This assertion WILL FAIL — status 200 is returned for invalid markdown.
    assert resp.status_code == 422, (
        "DISSERTATION FAILURE: The API accepted and returned a plain-text (non-markdown) "
        "response from Ollama without any structural validation. "
        "Status was 200 but should have been 422 to enforce response quality."
    )


# ---------------------------------------------------------------------------
# Fabric Simulation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fabric_simulate_success(genai_client, db_session):
    user = await _create_user(db_session, credits=50)
    mock_response = {
        "status": "success",
        "render_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    }

    with patch("genai.main.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=mock_response)

        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        resp = await genai_client.post(
            "/api/v1/genai/fabric/simulate",
            headers={"x-user-id": str(user.id)},
            json={
                "fabric": "Silk",
                "color": "#d8c7b5",
                "weight": 50,
                "stiffness": 30,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["fabric"] == "Silk"
    assert data["color"] == "#d8c7b5"
    assert data["render_base64"] == mock_response["render_base64"]

    # Verify credit deduction and DB persistence
    await db_session.refresh(user)
    assert user.credits == 45

    from sqlalchemy import select
    from common.models import FabricSimulation
    sim = await db_session.scalar(select(FabricSimulation).where(FabricSimulation.user_id == user.id))
    assert sim is not None
    assert sim.fabric_type == "Silk"
    assert sim.color == "#d8c7b5"
    assert sim.weight == 50
    assert sim.stiffness == 30
    assert sim.render_base64 == mock_response["render_base64"]



@pytest.mark.asyncio
async def test_fabric_simulate_no_auth(genai_client):
    resp = await genai_client.post(
        "/api/v1/genai/fabric/simulate",
        json={
            "fabric": "Silk",
            "color": "#d8c7b5",
            "weight": 50,
            "stiffness": 30,
        },
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_fabric_simulate_insufficient_credits(genai_client, db_session):
    user = await _create_user(db_session, credits=3)  # less than 5 cost
    resp = await genai_client.post(
        "/api/v1/genai/fabric/simulate",
        headers={"x-user-id": str(user.id)},
        json={
            "fabric": "Silk",
            "color": "#d8c7b5",
            "weight": 50,
            "stiffness": 30,
        },
    )
    assert resp.status_code == 402
    assert resp.json()["code"] == "insufficient_credits"


