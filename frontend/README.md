# Frontend

식물 주치의 AI의 사용자 화면 영역입니다. `frontend/design/`의 HTML 시안을 최대한 그대로 유지하기 위해 Vite + React 앱에서 원본 HTML을 직접 렌더링합니다.

## 권장 스택

- Vite + React + TypeScript
- Supabase Auth client
- API client는 `contracts/api/openapi.yaml` 기준으로 생성 또는 수동 정의
- 배포: Vercel 추천

## 예정 화면

- 로그인/회원가입/로그아웃
- 식물 목록
- 식물 등록
- 식물 상세
- 사진 업로드
- 재배일지 입력
- AI 상담 요청/결과
- 근거 문서 표시

## UI 파일 반영 흐름

1. AI가 만든 원본 UI 파일을 `frontend/ui-drop/`에 둡니다.
2. 불필요한 mock 데이터, 하드코딩 URL, secret이 없는지 확인합니다.
3. 실제 app 구조에 맞게 component/page 단위로 이동합니다.
4. API 호출은 `NEXT_PUBLIC_BACKEND_URL`을 사용합니다.
5. 로그인 상태와 token 전달을 연결합니다.

## 인증 기준

- 로그인/로그아웃은 Supabase Auth를 사용합니다.
- Backend API 요청에는 Supabase access token을 Bearer token으로 전달합니다.
- 로그인하지 않은 사용자는 식물 등록, 사진 업로드, AI 상담 화면에 접근하지 못하게 합니다.

## 로컬 실행

```bash
npm install
npm run dev
```

기본 개발 서버는 `http://127.0.0.1:3000/`입니다.

## 환경변수

`.env.local`에 아래 값을 설정합니다.

```bash
VITE_BACKEND_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

현재 화면은 디자인 시안 보존을 우선해 `frontend/design/*.html`을 그대로 표시합니다. Backend 연동 단계에서는 원본 시안을 기준으로 필요한 화면부터 React 컴포넌트화합니다.

## 배포

- Vercel project를 `frontend/` root 기준으로 연결합니다.
- public 환경변수만 Vercel에 등록합니다.
- `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`가 필수입니다.
