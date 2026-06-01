"""Sanity tests for the Catalog microservice — Image management & quota tracking."""
import io
import pytest
from sqlalchemy import select
from common.models import Image, ImageQuota, ImageType

# ---- per-service async clients ----

# ---------------------------------------------------------------------------
# Image tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_image_success(catalog_client):
    fake_image = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)  # minimal JPEG header
    resp = await catalog_client.post(
        "/api/v1/catalog/images/upload",
        files={"file": ("test.jpg", fake_image, "image/jpeg")},
        headers={"x-user-id": "1"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "url" in data
    assert data["url"].startswith("/uploads/")


@pytest.mark.asyncio
async def test_upload_image_invalid_mime(catalog_client):
    resp = await catalog_client.post(
        "/api/v1/catalog/images/upload",
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
        headers={"x-user-id": "1"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_image_no_user(catalog_client):
    fake_image = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)
    resp = await catalog_client.post(
        "/api/v1/catalog/images/upload",
        files={"file": ("test.jpg", fake_image, "image/jpeg")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_image_quota_enforcement(catalog_client):
    """Uploading more than DAILY_IMAGE_QUOTA images should return 429."""
    from common.config import settings
    quota = settings.daily_image_quota

    for _ in range(quota):
        img = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)
        r = await catalog_client.post(
            "/api/v1/catalog/images/upload",
            files={"file": ("img.jpg", img, "image/jpeg")},
            headers={"x-user-id": "42"},
        )
        assert r.status_code == 201

    # This one should be blocked
    img = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)
    r = await catalog_client.post(
        "/api/v1/catalog/images/upload",
        files={"file": ("img.jpg", img, "image/jpeg")},
        headers={"x-user-id": "42"},
    )
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_my_images(catalog_client):
    img = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100)
    await catalog_client.post(
        "/api/v1/catalog/images/upload",
        files={"file": ("img.jpg", img, "image/jpeg")},
        headers={"x-user-id": "7"},
    )
    resp = await catalog_client.get("/api/v1/catalog/images/me", headers={"x-user-id": "7"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_quota_status(catalog_client):
    resp = await catalog_client.get("/api/v1/catalog/images/quota", headers={"x-user-id": "99"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["used"] == 0
    assert "remaining" in data
