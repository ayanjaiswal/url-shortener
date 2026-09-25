import os


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://shortener:shortener@localhost:5432/shortener_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"


TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")
os.environ["REDIS_URL"] = TEST_REDIS_URL

from collections.abc import Callable, Iterator  

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.models  # noqa: E402, F401  (registers the tables on Base)
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.redis_client import redis_client  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    """Create all tables once per test run, and drop them afterwards."""
    assert engine.url.database is not None
    assert engine.url.database.endswith("_test"), "refusing to run tests on a non-test database"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    """Every test starts with empty tables."""
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, links RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def _clean_redis() -> Iterator[None]:
    """Every test starts with empty rate-limit buckets and empty cache entries."""
    yield
    redis_client.flushdb()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client: TestClient) -> Callable[..., dict[str, str]]:
    """Register + log in a user, and return the Authorization header to use in requests."""

    def _make(email: str = "user@example.com", password: str = "supersecret1") -> dict[str, str]:
        registered = client.post("/auth/register", json={"email": email, "password": password})
        assert registered.status_code == 201
        login = client.post("/auth/login", data={"username": email, "password": password})
        assert login.status_code == 200
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    return _make