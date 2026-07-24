# Frontend

Farm하니의 사용자 화면 영역입니다. Vite + React + TypeScript 기반의 네이티브 컴포넌트로 로그인, 식물 관리, 기록, AI 상태 점검 흐름을 제공합니다.

## 권장 스택

- Vite + React + TypeScript
- Supabase Auth client
- API client는 `contracts/api/openapi.yaml` 기준으로 생성 또는 수동 정의
- 배포: Vercel 추천

## 제공 화면

- 로그인/회원가입/로그아웃
- 식물 목록
- 식물 등록
- 식물 상세
- 사진 업로드
- 재배일지 입력
- 물주기 알림 목록 및 브라우저 알림 설정
- AI 상담 요청/결과
- 근거 문서 표시

## UI 파일 반영 흐름

1. AI가 만든 원본 UI 파일을 `frontend/ui-drop/`에 둡니다.
2. 불필요한 mock 데이터, 하드코딩 URL, secret이 없는지 확인합니다.
3. 실제 app 구조에 맞게 component/page 단위로 이동합니다.
4. API 호출은 `VITE_BACKEND_URL`을 사용합니다.
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

개발 중에만 mock 데이터를 명시적으로 사용하려면 아래 값을 추가합니다.

```bash
VITE_ENABLE_MOCKS=true
```

mock은 Vite의 `development` 모드에서만 활성화됩니다. 프로덕션에서는 환경변수가 누락되더라도 mock 결과를 표시하지 않고 연결 설정 오류를 사용자에게 안내합니다.

이전 HTML 시안은 비교용으로 `frontend/design/`에만 보존되어 있으며 실행 앱과 배포 결과에서는 로드하지 않습니다.

## 배포

- Vercel project를 `frontend/` root 기준으로 연결합니다.
- public 환경변수만 Vercel에 등록합니다.
- `VITE_BACKEND_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`가 필수입니다.
- `VITE_ENABLE_MOCKS`는 프로덕션에 등록하지 않습니다.
