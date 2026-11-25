
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.auth import redis as redis_module


@pytest.fixture(autouse=True)
def clear_redis_cache():
    """Remove the cached Redis client before and after each test."""
    if hasattr(redis_module.get_redis, "redis"):
        delattr(redis_module.get_redis, "redis")

    yield

    if hasattr(redis_module.get_redis, "redis"):
        delattr(redis_module.get_redis, "redis")


# -------------------------
# get_redis()
# -------------------------

def test_get_redis_initializes_client(monkeypatch):
    fake_client = AsyncMock()
    mock_from_url = AsyncMock(return_value=fake_client)

    monkeypatch.setattr(
        redis_module.aioredis,
        "from_url",
        mock_from_url,
    )

    result = asyncio.run(redis_module.get_redis())

    assert result is fake_client
    mock_from_url.assert_awaited_once_with(
        redis_module.settings.REDIS_URL or "redis://localhost"
    )


def test_get_redis_reuses_existing_client(monkeypatch):
    fake_client = AsyncMock()

    redis_module.get_redis.redis = fake_client

    mock_from_url = AsyncMock()

    monkeypatch.setattr(
        redis_module.aioredis,
        "from_url",
        mock_from_url,
    )

    result = asyncio.run(redis_module.get_redis())

    assert result is fake_client
    mock_from_url.assert_not_awaited()


# -------------------------
# add_to_blacklist()
# -------------------------

def test_add_to_blacklist(monkeypatch):
    fake_redis = AsyncMock()

    monkeypatch.setattr(
        redis_module,
        "get_redis",
        AsyncMock(return_value=fake_redis),
    )

    asyncio.run(
        redis_module.add_to_blacklist("test-jti-123", 3600)
    )

    fake_redis.set.assert_awaited_once_with(
        "blacklist:test-jti-123",
        "1",
        ex=3600,
    )


# -------------------------
# is_blacklisted()
# -------------------------

def test_is_blacklisted_returns_true(monkeypatch):
    fake_redis = AsyncMock()
    fake_redis.exists.return_value = 1

    monkeypatch.setattr(
        redis_module,
        "get_redis",
        AsyncMock(return_value=fake_redis),
    )

    result = asyncio.run(
        redis_module.is_blacklisted("test-jti-123")
    )

    assert result == 1
    fake_redis.exists.assert_awaited_once_with(
        "blacklist:test-jti-123"
    )


def test_is_blacklisted_returns_false(monkeypatch):
    fake_redis = AsyncMock()
    fake_redis.exists.return_value = 0

    monkeypatch.setattr(
        redis_module,
        "get_redis",
        AsyncMock(return_value=fake_redis),
    )

    result = asyncio.run(
        redis_module.is_blacklisted("unknown-jti")
    )

    assert result == 0
    fake_redis.exists.assert_awaited_once_with(
        "blacklist:unknown-jti"
    )