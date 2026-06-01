"""Sanity tests for Analytics and Audit microservices."""
import pytest


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_track_event(analytics_client):
    resp = await analytics_client.post(
        "/api/v1/analytics/track",
        json={"service": "auth", "event_type": "user_login", "user_id": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_track_event_no_user(analytics_client):
    resp = await analytics_client.post(
        "/api/v1/analytics/track",
        json={"service": "catalog", "event_type": "product_view"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_usage_stats_empty(analytics_client):
    resp = await analytics_client.get("/api/v1/analytics/stats/usage")
    assert resp.status_code == 200
    assert "stats" in resp.json()


@pytest.mark.asyncio
async def test_usage_stats_populated(analytics_client):
    for _ in range(3):
        await analytics_client.post(
            "/api/v1/analytics/track",
            json={"service": "orders", "event_type": "order_placed"},
        )
    resp = await analytics_client.get("/api/v1/analytics/stats/usage")
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    order_stat = next((s for s in stats if s["event_type"] == "order_placed"), None)
    assert order_stat is not None
    assert order_stat["count"] == 3


@pytest.mark.asyncio
async def test_daily_stats(analytics_client):
    await analytics_client.post(
        "/api/v1/analytics/track",
        json={"service": "auth", "event_type": "register"},
    )
    resp = await analytics_client.get("/api/v1/analytics/stats/daily", params={"days": 7})
    assert resp.status_code == 200
    assert "stats" in resp.json()


@pytest.mark.asyncio
async def test_user_activity(analytics_client):
    for uid in [1, 1, 2]:
        await analytics_client.post(
            "/api/v1/analytics/track",
            json={"service": "catalog", "event_type": "view", "user_id": uid},
        )
    resp = await analytics_client.get("/api/v1/analytics/stats/users")
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats[0]["user_id"] == 1  # user 1 has 2 events vs user 2's 1


@pytest.mark.asyncio
async def test_raw_events_list(analytics_client):
    await analytics_client.post(
        "/api/v1/analytics/track",
        json={"service": "catalog", "event_type": "image_upload"},
    )
    resp = await analytics_client.get("/api/v1/analytics/events")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_events_filter_by_service(analytics_client):
    await analytics_client.post(
        "/api/v1/analytics/track",
        json={"service": "auth", "event_type": "login"},
    )
    await analytics_client.post(
        "/api/v1/analytics/track",
        json={"service": "catalog", "event_type": "view"},
    )
    resp = await analytics_client.get("/api/v1/analytics/events", params={"service": "auth"})
    assert resp.status_code == 200
    events = resp.json()
    assert all(e["service"] == "auth" for e in events)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_accepted(audit_client):
    resp = await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "auth", "level": "INFO", "message": "User registered"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_audit_log_invalid_level(audit_client):
    resp = await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "auth", "level": "TRACE", "message": "blah"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_search_empty(audit_client):
    resp = await audit_client.get("/api/v1/audit/search")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_audit_search_with_results(audit_client):
    await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "orders", "level": "ERROR", "message": "DB connection failed"},
    )
    resp = await audit_client.get("/api/v1/audit/search", params={"service": "orders", "level": "ERROR"})
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    assert logs[0]["service_name"] == "orders"


@pytest.mark.asyncio
async def test_audit_search_message_contains(audit_client):
    await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "catalog", "level": "WARN", "message": "Quota nearly exceeded"},
    )
    resp = await audit_client.get("/api/v1/audit/search", params={"message_contains": "Quota"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_audit_get_by_id(audit_client):
    await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "gateway", "level": "INFO", "message": "Request received"},
    )
    search = await audit_client.get("/api/v1/audit/search")
    log_id = search.json()[0]["id"]

    resp = await audit_client.get(f"/api/v1/audit/logs/{log_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == log_id


@pytest.mark.asyncio
async def test_audit_get_by_id_not_found(audit_client):
    resp = await audit_client.get("/api/v1/audit/logs/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_stats(audit_client):
    await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "auth", "level": "INFO", "message": "Login"},
    )
    resp = await audit_client.get("/api/v1/audit/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "stats" in data
    assert "period_days" in data


@pytest.mark.asyncio
async def test_audit_health(audit_client):
    resp = await audit_client.get("/api/v1/audit/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_audit_purge(audit_client):
    await audit_client.post(
        "/api/v1/audit/log",
        json={"service_name": "analytics", "level": "DEBUG", "message": "tick"},
    )
    resp = await audit_client.delete("/api/v1/audit/purge", params={"older_than_days": 1})
    assert resp.status_code == 204
