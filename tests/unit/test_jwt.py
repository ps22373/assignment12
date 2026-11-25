import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

import app.auth.jwt as jwt_module
from app.schemas.token import TokenType


# Password hashing

def test_password_hash_and_verify():
    password = "TestPass123"

    hashed = jwt_module.get_password_hash(password)

    assert hashed != password
    assert jwt_module.verify_password(password, hashed) is True
    assert jwt_module.verify_password("WrongPass123", hashed) is False


# Token creation

def test_create_access_token():
    user_id = uuid4()

    token = jwt_module.create_token(user_id, TokenType.ACCESS)
    payload = jose_jwt.decode(
        token,
        jwt_module.settings.JWT_SECRET_KEY,
        algorithms=[jwt_module.settings.ALGORITHM],
    )

    assert payload["sub"] == str(user_id)
    assert payload["type"] == TokenType.ACCESS.value
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_create_refresh_token():
    token = jwt_module.create_token("user123", TokenType.REFRESH)

    payload = jose_jwt.decode(
        token,
        jwt_module.settings.JWT_REFRESH_SECRET_KEY,
        algorithms=[jwt_module.settings.ALGORITHM],
    )

    assert payload["sub"] == "user123"
    assert payload["type"] == TokenType.REFRESH.value


def test_create_token_with_custom_expiration():
    token = jwt_module.create_token(
        "user123",
        TokenType.ACCESS,
        expires_delta=timedelta(minutes=5),
    )

    payload = jose_jwt.decode(
        token,
        jwt_module.settings.JWT_SECRET_KEY,
        algorithms=[jwt_module.settings.ALGORITHM],
    )

    expiration = datetime.fromtimestamp(payload["exp"], timezone.utc)
    issued_at = datetime.fromtimestamp(payload["iat"], timezone.utc)

    assert timedelta(minutes=4) < expiration - issued_at < timedelta(minutes=6)


def test_create_token_encoding_failure(monkeypatch):
    def raise_error(*args, **kwargs):
        raise ValueError("Encoding failed")

    monkeypatch.setattr(jwt_module.jwt, "encode", raise_error)

    with pytest.raises(HTTPException) as exc:
        jwt_module.create_token("user123", TokenType.ACCESS)

    assert exc.value.status_code == 500
    assert "Could not create token" in exc.value.detail


# Token decoding

def test_decode_valid_access_token(monkeypatch):
    token = jwt_module.create_token("user123", TokenType.ACCESS)
    monkeypatch.setattr(
        jwt_module,
        "is_blacklisted",
        AsyncMock(return_value=False),
    )

    payload = asyncio.run(
        jwt_module.decode_token(token, TokenType.ACCESS)
    )

    assert payload["sub"] == "user123"


def test_decode_valid_refresh_token(monkeypatch):
    token = jwt_module.create_token("user123", TokenType.REFRESH)
    monkeypatch.setattr(
        jwt_module,
        "is_blacklisted",
        AsyncMock(return_value=False),
    )

    payload = asyncio.run(
        jwt_module.decode_token(token, TokenType.REFRESH)
    )

    assert payload["type"] == TokenType.REFRESH.value



def test_decode_token_wrong_type(monkeypatch):
    token = jwt_module.create_token("user123", TokenType.REFRESH)

    monkeypatch.setattr(
        jwt_module.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "user123",
            "type": TokenType.REFRESH.value,
            "jti": "test-token",
        },
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            jwt_module.decode_token(token, TokenType.ACCESS)
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token type"


def test_decode_blacklisted_token(monkeypatch):
    token = jwt_module.create_token("user123", TokenType.ACCESS)

    monkeypatch.setattr(
        jwt_module,
        "is_blacklisted",
        AsyncMock(return_value=True),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            jwt_module.decode_token(token, TokenType.ACCESS)
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has been revoked"


def test_decode_expired_token():
    expired_payload = {
        "sub": "user123",
        "type": TokenType.ACCESS.value,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        "jti": "expired-token",
    }

    token = jose_jwt.encode(
        expired_payload,
        jwt_module.settings.JWT_SECRET_KEY,
        algorithm=jwt_module.settings.ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            jwt_module.decode_token(token, TokenType.ACCESS)
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has expired"


def test_decode_malformed_token():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            jwt_module.decode_token("not.a.valid.token", TokenType.ACCESS)
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Could not validate credentials"


def test_decode_token_without_expiration_verification(monkeypatch):
    token = jwt_module.create_token("user123", TokenType.ACCESS)

    monkeypatch.setattr(
        jwt_module,
        "is_blacklisted",
        AsyncMock(return_value=False),
    )

    payload = asyncio.run(
        jwt_module.decode_token(
            token,
            TokenType.ACCESS,
            verify_exp=False,
        )
    )

    assert payload["sub"] == "user123"


# Current user dependency

def test_get_current_user_success(monkeypatch):
    user_id = str(uuid4())
    expected_user = SimpleNamespace(is_active=True)

    monkeypatch.setattr(
        jwt_module,
        "decode_token",
        AsyncMock(return_value={"sub": user_id}),
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = expected_user

    result = asyncio.run(
        jwt_module.get_current_user(token="valid-token", db=db)
    )

    assert result is expected_user


def test_get_current_user_not_found(monkeypatch):
    monkeypatch.setattr(
        jwt_module,
        "decode_token",
        AsyncMock(return_value={"sub": str(uuid4())}),
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            jwt_module.get_current_user(token="valid-token", db=db)
        )

    # The current implementation catches the original 404 and converts it into a 401.
    assert exc.value.status_code == 401
    assert "User not found" in exc.value.detail


def test_get_current_user_inactive(monkeypatch):
    inactive_user = SimpleNamespace(is_active=False)

    monkeypatch.setattr(
        jwt_module,
        "decode_token",
        AsyncMock(return_value={"sub": str(uuid4())}),
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = inactive_user

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            jwt_module.get_current_user(token="valid-token", db=db)
        )

    assert exc.value.status_code == 401
    assert "Inactive user" in exc.value.detail