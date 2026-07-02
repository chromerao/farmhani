# 테스트용 토큰 발급기 입니다!

import sys
import os
from supabase import create_client

# 현재 디렉터리 경로를 추가하여 app 모듈을 가져옵니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def main():
    print("Supabase URL:", settings.SUPABASE_URL)
    
    email = "testuser@example.com"
    password = "TestPassword123!"
    
    # 1. 관리자 권한(SERVICE_ROLE_KEY)으로 이메일이 자동 확인된(email_confirm=True) 사용자 생성
    try:
        admin_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        admin_supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        print("관리자 권한으로 테스트 유저 생성 및 자동 승인 완료!")
    except Exception as e:
        # 이미 존재하거나 생성 오류가 발생해도 로그인을 위해 계속 진행합니다.
        pass

    # 2. 퍼블릭 anon key 클라이언트로 로그인하여 JWT 토큰 획득
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        token = response.session.access_token
        print("\n=== 복사할 Bearer 토큰 값 ===")
        print(token)
        print("=============================\n")
    except Exception as e:
        print("로그인 중 오류 발생:", str(e))
        print("참고: Supabase 설정에서 이메일 로그인이 비활성화되어 있거나 패스워드가 다를 수 있습니다.")

if __name__ == "__main__":
    main()
