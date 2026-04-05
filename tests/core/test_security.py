import pytest
import jwt
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.core.security import (
    create_token,
    decode_token,
    create_refresh_token,
    blacklist_token,
    is_blacklisted,
    ALGORITHM,
)
from app.core.config import settings


class TestCreateToken:
    def test_returns_valid_jwt(self):
        token = create_token(sub="user-1", role="customer")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-1"
        assert payload["role"] == "customer"
        assert "exp" in payload
        assert "jti" in payload

    def test_default_role_is_user(self):
        token = create_token(sub="user-2")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        assert payload["role"] == "user"

    def test_custom_expiration(self):
        token = create_token(sub="user-3", expires_in=60)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        # exp should be roughly 60s from now
        exp_dt = datetime.utcfromtimestamp(payload["exp"])
        assert exp_dt < datetime.utcnow() + timedelta(seconds=65)
        assert exp_dt > datetime.utcnow() + timedelta(seconds=50)


class TestDecodeToken:
    def test_decode_valid_token(self):
        token = create_token(sub="user-1", role="admin")
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "admin"

    def test_decode_expired_token_raises(self):
        token = create_token(sub="user-1", expires_in=-1)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_invalid_token_raises(self):
        with pytest.raises(jwt.PyJWTError):
            decode_token("not.a.valid.token")


class TestCreateRefreshToken:
    def test_returns_refresh_token(self):
        token = create_refresh_token(sub="user-1")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"
        assert "exp" in payload


class TestBlacklistToken:
    def test_calls_redis_setex(self):
        redis_mock = MagicMock()
        blacklist_token("jti-123", 3600, redis_mock)
        redis_mock.setex.assert_called_once_with("blacklist:jti-123", 3600, "1")


class TestIsBlacklisted:
    def test_returns_true_when_exists(self):
        redis_mock = MagicMock()
        redis_mock.exists.return_value = 1
        assert is_blacklisted("jti-123", redis_mock) is True
        redis_mock.exists.assert_called_once_with("blacklist:jti-123")

    def test_returns_false_when_not_exists(self):
        redis_mock = MagicMock()
        redis_mock.exists.return_value = 0
        assert is_blacklisted("jti-123", redis_mock) is False
