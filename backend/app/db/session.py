from supabase import create_client, Client
from app.core.config import settings

# 글로벌 Supabase 클라이언트 인스턴스 초기화
# settings에 주입된 Supabase URL과 Anon Key를 사용해 클라이언트를 만듭니다.
supabase: Client = create_client(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_ANON_KEY
)

def get_supabase_client() -> Client:
    """
    FastAPI API 핸들러에서 Dependency Injection(의존성 주입)으로 
    Supabase 클라이언트를 가져와서 사용할 수 있도록 제공하는 헬퍼 함수입니다.
    """
    return supabase
