"""
tests/conftest.py — Shared pytest fixtures
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from db.database import Base, get_db
from auth.auth import hash_password
from db.models import User
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, future=True)
TestSession  = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        session.add(User(id="test-user-id", username="testuser", email="test@lexai.dev",
                         hashed_password=hash_password("testpass123"), is_active=True))
        await session.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def auth_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/auth/login", data={"username": "testuser", "password": "testpass123"})
        assert resp.status_code == 200
        client.headers.update({"Authorization": f"Bearer {resp.json()['access_token']}"})
        yield client


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


MOCK_PIPELINE_RESULT = {
    "research":    {"content": "• Contract Law\n• Key issues: breach\n• UCC § 2-301\n• Preponderance\n• Hadley v Baxendale"},
    "defense":     {"content": "• No intentional breach\n• Failed to mitigate\n• Terms ambiguous\n• Substantial performance"},
    "prosecution": {"content": "• Clear contract terms\n• Full consideration received\n• Documented damages\n• Written obligations confirmed"},
    "verdict":     {"ruling": "Liable", "confidence": 72,
                    "reasoning": "Weight of evidence supports liability.",
                    "key_finding": "Written communications confirm obligations."},
}
