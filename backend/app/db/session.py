from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client, ClientOptions
from app.core.config import settings

# FastAPI의 기본 HTTP Bearer 인증 체계를 가져옵니다.
# Swagger UI에 자물쇠 버튼이 생기고 'Authorization: Bearer <JWT>' 헤더를 파싱해 줍니다.
reusable_oauth2 = HTTPBearer()

# 글로벌 Supabase 클라이언트 인스턴스 초기화 (비인증용/RAG 백업용)
supabase: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_ANON_KEY
)

def get_supabase_service_client() -> Client:
    """
    Server-side Supabase client for trusted operations such as Storage uploads.
    It must never be exposed to browser code.
    """
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=service_key,
        options=ClientOptions(persist_session=False)
    )

def get_supabase_client(
    credentials: HTTPAuthorizationCredentials = Depends(reusable_oauth2)
) -> Client:
    """
    각 요청마다 사용자 JWT(Bearer Token)를 헤더에서 추출하여 
    동적으로 생성되는 요청-스코프(Request-Scoped) Supabase 클라이언트입니다.
    이를 통해 Supabase Row-Level Security(RLS) 정책이 안전하게 적용됩니다.
    """
    token = credentials.credentials
    client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
        options=ClientOptions(
            persist_session=False,
            headers={"Authorization": f"Bearer {token}"}
        )
    )
    client.postgrest.auth(token)
    return client
