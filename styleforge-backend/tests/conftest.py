"""
Shared test fixtures:
- In-memory SQLite database (avoids needing a live Postgres)
- TestClient for each service app
"""
import os
import sys

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Ensure common is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use SQLite for tests (avoids needing Postgres)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

os.environ.setdefault("POSTGRES_URL", TEST_DB_URL)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("DAILY_IMAGE_QUOTA", "5")

from common.database import Base
from common import models  # noqa: F401 – registers all models

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


# ---- per-service async clients ----

@pytest_asyncio.fixture
async def auth_client(db_engine):
    from auth.main import app
    import common.database as db_mod
    db_mod.engine = db_engine
    db_mod.async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with db_mod.async_session() as session:
            yield session

    app.dependency_overrides[db_mod.get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def catalog_client(db_engine, tmp_path):
    from catalog.main import app
    import catalog.main as catalog_mod
    import common.database as db_mod

    catalog_mod.UPLOAD_DIR = str(tmp_path)
    db_mod.engine = db_engine
    db_mod.async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with db_mod.async_session() as session:
            yield session

    app.dependency_overrides[db_mod.get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()





@pytest_asyncio.fixture
async def analytics_client(db_engine):
    from analytics.main import app
    import common.database as db_mod
    db_mod.engine = db_engine
    db_mod.async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with db_mod.async_session() as session:
            yield session

    app.dependency_overrides[db_mod.get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def audit_client(db_engine):
    from audit.main import app
    import common.database as db_mod
    db_mod.engine = db_engine
    db_mod.async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with db_mod.async_session() as session:
            yield session

    app.dependency_overrides[db_mod.get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
