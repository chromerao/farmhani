import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from supabase_auth.errors import AuthApiError, AuthRetryableError

from app.auth import security


TEST_USER_ID = uuid.UUID("64f58b4f-ed66-4cf3-8e63-a97548697217")
CREDENTIALS = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


class StubAuth:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error

    def get_user(self, token: str):
        assert token == "test-token"
        if self.error:
            raise self.error
        return self.result


class StubSupabase:
    def __init__(self, auth: StubAuth):
        self.auth = auth


def force_remote_fallback(monkeypatch: pytest.MonkeyPatch, auth: StubAuth) -> None:
    monkeypatch.setattr(security, "_verify_token_locally", lambda _token: None)
    monkeypatch.setattr(security, "supabase", StubSupabase(auth))


def test_invalid_local_token_returns_401_without_remote_fallback(monkeypatch: pytest.MonkeyPatch):
    called = False

    def reject_token(_token: str):
        raise jwt.InvalidTokenError("invalid")

    class UnexpectedAuth:
        def get_user(self, _token: str):
            nonlocal called
            called = True

    monkeypatch.setattr(security, "_verify_token_locally", reject_token)
    monkeypatch.setattr(security, "supabase", StubSupabase(UnexpectedAuth()))

    with pytest.raises(HTTPException) as caught:
        security.get_current_user(CREDENTIALS)

    assert caught.value.status_code == 401
    assert called is False


def test_retryable_auth_outage_returns_503(monkeypatch: pytest.MonkeyPatch):
    force_remote_fallback(monkeypatch, StubAuth(error=AuthRetryableError("temporary", 503)))

    with pytest.raises(HTTPException) as caught:
        security.get_current_user(CREDENTIALS)

    assert caught.value.status_code == 503


def test_remote_invalid_token_still_returns_401(monkeypatch: pytest.MonkeyPatch):
    force_remote_fallback(monkeypatch, StubAuth(error=AuthApiError("invalid", 401, "bad_jwt")))

    with pytest.raises(HTTPException) as caught:
        security.get_current_user(CREDENTIALS)

    assert caught.value.status_code == 401


def test_remote_fallback_returns_authenticated_user(monkeypatch: pytest.MonkeyPatch):
    response = type("AuthResponse", (), {"user": type("User", (), {"id": str(TEST_USER_ID)})()})()
    force_remote_fallback(monkeypatch, StubAuth(result=response))

    assert security.get_current_user(CREDENTIALS) == TEST_USER_ID


def test_local_verification_accepts_small_clock_skew(monkeypatch: pytest.MonkeyPatch):
    secret = "test-secret-with-enough-length-for-hs256"
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(TEST_USER_ID),
            "aud": "authenticated",
            "iat": now + timedelta(seconds=5),
            "exp": now + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )
    monkeypatch.setattr(security.settings, "SUPABASE_JWT_SECRET", secret)
    monkeypatch.setattr(security.settings, "JWT_AUDIENCE", "authenticated")

    assert security._verify_token_locally(token) == TEST_USER_ID
