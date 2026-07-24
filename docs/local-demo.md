# Farm하니 로컬 실데이터 데모

이 문서는 mock 데이터가 아닌 Supabase Auth·Postgres·Storage와 FastAPI·RAG를 연결해 프론트엔드 데모를 실행하는 방법을 설명합니다.

## 1. 환경변수 확인

프로젝트 루트의 `.env`에 아래 항목을 설정합니다. 실제 값은 Git에 커밋하지 않습니다.

```dotenv
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_SUPABASE_STORAGE_BUCKET=plant-photos

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=plant-photos
OPENAI_API_KEY=
```

`VITE_ENABLE_MOCKS=true`가 설정되어 있으면 개발 서버가 mock 데이터를 사용합니다. 실데이터 데모에서는 이 항목을 제거하거나 `false`로 설정합니다.

## 2. 백엔드 실행

PowerShell 터미널 1에서 실행합니다.

```powershell
cd C:\Users\playdata2\SKN30-3rd-3Team
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 `http://127.0.0.1:8000/health`를 열어 `status`가 `healthy`인지 확인합니다.

## 3. 프론트엔드 실행

PowerShell 터미널 2에서 실행합니다.

```powershell
cd C:\Users\playdata2\SKN30-3rd-3Team\frontend
Remove-Item Env:VITE_ENABLE_MOCKS -ErrorAction SilentlyContinue
npm install
npm run dev -- --host 127.0.0.1 --port 3000 --strictPort
```

`http://127.0.0.1:3000/`에 접속한 뒤 Supabase 계정으로 로그인합니다.

## 4. 데모 권장 순서

1. 회원가입 또는 로그인
2. 첫 식물 등록
3. 식물 상세에서 잎·흙 상태와 메모 저장
4. 관찰 사진 업로드
5. AI 상담에서 식물을 선택하고 질문 전송
6. 구조화된 답변, 근거 문서 링크, 안전 안내 확인
7. 체크리스트와 알림 상태 확인

AI 상담 입력창은 `Enter`로 전송하고 `Shift+Enter`로 줄을 바꿉니다.

## 5. production 빌드 확인

```powershell
cd C:\Users\playdata2\SKN30-3rd-3Team\frontend
npm run build
npm run preview
```

서비스워커는 새 배포를 감지하면 최신 앱 셸로 교체합니다. 이전 mock 화면이 계속 보이면 개발자 도구에서 기존 서비스워커와 사이트 캐시를 한 번 제거한 뒤 새로고침합니다.

## 6. 문제 확인

- `401` 또는 `403`: 다시 로그인해 Supabase access token을 갱신합니다.
- CORS 오류: 백엔드 `CORS_ORIGINS`에 `http://127.0.0.1:3000`이 포함됐는지 확인합니다.
- 식물 도감 검색 실패: 백엔드의 `/api/v1/plant-catalog` 응답과 Supabase `plant_catalog` 데이터를 확인합니다.
- 사진 업로드 실패: `plant-photos` 버킷과 `SUPABASE_STORAGE_BUCKET` 값이 일치하는지 확인합니다.
- AI 답변 실패: `OPENAI_API_KEY`, RAG 테이블 데이터, 백엔드 로그를 확인합니다.
