"""Sanity tests for the Auth microservice."""
import pytest


@pytest.mark.asyncio
async def test_register_success(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "secure1234"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client):
    payload = {"email": "bob@example.com", "password": "secure1234"}
    await auth_client.post("/api/v1/auth/register", json=payload)
    resp = await auth_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "123"},
    )
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_login_success(auth_client):
    await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "password123"},
    )
    resp = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "carol@example.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client):
    await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "dave@example.com", "password": "correct-pass"},
    )
    resp = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "dave@example.com", "password": "wrong-pass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "pass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(auth_client):
    resp = await auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile(auth_client):
    reg = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]
    resp = await auth_client.get(
        "/api/v1/auth/me",
        headers={"x-user-id": str(user_id)},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "eve@example.com"


from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch("auth.main._send_otp_email", new_callable=AsyncMock)
@patch("auth.main.random.randint")
async def test_otp_request_and_verify(mock_randint, mock_send, auth_client):
    mock_randint.return_value = 123456
    # Request OTP
    resp = await auth_client.post(
        "/api/v1/auth/login/otp/request",
        json={"email": "otp@example.com"},
    )
    assert resp.status_code == 200

    # Verify OTP (we know it's "123456")
    resp2 = await auth_client.post(
        "/api/v1/auth/login/otp/verify",
        json={"email": "otp@example.com", "otp": "123456"},
    )
    assert resp2.status_code == 200
    assert "access_token" in resp2.json()


@pytest.mark.asyncio
@patch("auth.main._send_otp_email", new_callable=AsyncMock)
async def test_otp_wrong_code(mock_send, auth_client):
    await auth_client.post("/api/v1/auth/login/otp/request", json={"email": "bad@example.com"})
    resp = await auth_client.post(
        "/api/v1/auth/login/otp/verify",
        json={"email": "bad@example.com", "otp": "000000"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_role(auth_client):
    reg = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "role@example.com", "password": "password123"},
    )
    user_id = reg.json()["user"]["id"]
    resp = await auth_client.put(
        "/api/v1/auth/me/role",
        json={"role": "tailor"},
        headers={"x-user-id": str(user_id)},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "tailor"


@pytest.mark.asyncio
async def test_update_role_invalid(auth_client):
    reg = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "badrole@example.com", "password": "password123"},
    )
    user_id = reg.json()["user"]["id"]
    resp = await auth_client.put(
        "/api/v1/auth/me/role",
        json={"role": "superadmin"},
        headers={"x-user-id": str(user_id)},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token_success(auth_client):
    reg = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    
    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "refresh@example.com"


@pytest.mark.asyncio
async def test_refresh_token_invalid(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"token": "some-invalid-garbage-token"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_token"
