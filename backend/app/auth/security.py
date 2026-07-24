import logging
import uuid

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from supabase_auth.errors import AuthApiError, AuthInvalidJwtError, AuthRetryableError, AuthUnknownError

from app.core.config import settings
from app.db.session import supabase, reusable_oauth2

logger = logging.getLogger(__name__)

_INVALID_TOKEN_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="만료되거나 올바르지 않은 토큰입니다."
)
_AUTH_SERVICE_UNAVAILABLE_ERROR = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="인증 서버 연결이 원활하지 않습니다. 잠시 후 다시 시도해 주세요."
)

# JWKS 공개키는 프로세스 수명 동안 캐시된다 (PyJWKClient 내부 캐시 + lifespan)
_jwk_client: PyJWKClient | None = None
_JWT_CLOCK_SKEW_LEEWAY_SECONDS = 30


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwk_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwk_client


def _verify_token_locally(token: str) -> uuid.UUID | None:
    """
    Supabase JWT를 네트워크 왕복 없이 로컬에서 검증한다.

    반환 None = 로컬 검증을 수행할 수 없는 환경(키 없음/미지원 알고리즘)으로,
    호출자는 Supabase Auth API 폴백을 사용해야 한다.
    서명 불일치/만료/audience 불일치는 jwt.InvalidTokenError로 전파된다.
    """
    header = jwt.get_unverified_header(token)
    alg = str(header.get("alg") or "")

    if alg.startswith("HS"):
        # 레거시 프로젝트: 공유 시크릿(HS256) 서명 — SUPABASE_JWT_SECRET 필요
        if not settings.SUPABASE_JWT_SECRET:
            return None
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[alg],
            audience=settings.JWT_AUDIENCE,
            leeway=_JWT_CLOCK_SKEW_LEEWAY_SECONDS,
        )
    elif alg in {"RS256", "RS512", "ES256", "ES512", "EdDSA"}:
        # 신규 프로젝트: JWKS 공개키(비대칭) 서명
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=settings.JWT_AUDIENCE,
            leeway=_JWT_CLOCK_SKEW_LEEWAY_SECONDS,
        )
    else:
        return None

    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("missing sub claim")
    return uuid.UUID(sub)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(reusable_oauth2)
) -> uuid.UUID:
    """
    FastAPI 전용 인증 Dependency입니다.

    1순위: JWT 서명을 로컬에서 검증한다 (요청당 Supabase 왕복 제거).
    2순위: 로컬 검증이 불가능한 환경에서만 Supabase Auth API(get_user)로 폴백한다.
    """
    token = credentials.credentials

    try:
        user_id = _verify_token_locally(token)
        if user_id is not None:
            return user_id
    except jwt.InvalidTokenError:
        # 서명 위조/만료/audience 불일치 — 폴백 없이 즉시 거부
        raise _INVALID_TOKEN_ERROR
    except Exception as exc:
        # JWKS 조회 실패 등 인프라성 오류 — 네트워크 검증으로 폴백
        logger.warning("로컬 JWT 검증 불가, Supabase Auth 폴백 사용: %s", exc)

    try:
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise _INVALID_TOKEN_ERROR
        return uuid.UUID(auth_response.user.id)
    except HTTPException:
        raise
    except AuthInvalidJwtError:
        raise _INVALID_TOKEN_ERROR
    except AuthApiError as exc:
        if exc.status in {401, 403}:
            raise _INVALID_TOKEN_ERROR
        logger.warning("Supabase Auth API 검증 실패: status=%s code=%s", exc.status, exc.code)
        raise _AUTH_SERVICE_UNAVAILABLE_ERROR
    except (AuthRetryableError, AuthUnknownError) as exc:
        logger.warning("Supabase Auth 일시 오류: %s", exc)
        raise _AUTH_SERVICE_UNAVAILABLE_ERROR
    except Exception:
        logger.exception("Supabase Auth 검증 중 예기치 않은 오류")
        raise _AUTH_SERVICE_UNAVAILABLE_ERROR
