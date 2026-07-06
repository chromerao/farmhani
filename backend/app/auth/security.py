import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from app.db.session import supabase, reusable_oauth2


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(reusable_oauth2)
) -> uuid.UUID:
    """
    FastAPI 전용 인증 Dependency입니다.
    
    1. HTTP 요청 헤더에서 JWT(Access Token)를 안전하게 파싱합니다.
    2. Supabase Auth의 get_user(token) API를 사용해 토큰의 진위와 만료 여부를 판별합니다.
    3. 검증에 통과하면 사용자의 고유 UUID 식별자를 반환합니다.
    4. 토큰이 비어 있거나 만료/위조되었다면 즉시 401 Unauthorized 에러를 발생시킵니다.
    """
    token = credentials.credentials
    try:
        # Supabase API 서버를 통해 토큰을 검증하고 유저 데이터를 가져옵니다.
        auth_response = supabase.auth.get_user(token)
        
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증 정보를 확인할 수 없습니다. 유효하지 않은 응답입니다."
            )
        
        # 데이터베이스 스키마(UUID 형식)와 맞추기 위해 UUID 객체로 변환하여 넘겨줍니다.
        return uuid.UUID(auth_response.user.id)
        
    except HTTPException:
        raise
    except Exception:
        # 내부 예외 문자열을 클라이언트에 노출하지 않는다 (스키마/엔드포인트 정보 유출 방지)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="만료되거나 올바르지 않은 토큰입니다."
        )
