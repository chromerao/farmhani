# Frontend Agent 지침

## 작업 범위

- 수정 가능: `frontend/`
- 읽기 권장: `contracts/api/openapi.yaml`, `docs/api-contract.md`
- 수정 전 합의 필요: `contracts/`, root `README.md`, root `AGENTS.md`

## 책임

- 로그인/로그아웃 UI
- 식물 등록/목록/상세 화면
- 사진 업로드 화면
- 재배일지 입력 화면
- AI 상담 결과 화면
- Backend API 연동

## 보안 규칙

- 프론트에는 public 환경변수만 사용합니다.
- `SUPABASE_SERVICE_ROLE_KEY`, DB URL, server-only API key를 절대 넣지 않습니다.
- 사용자의 access token은 Backend 요청 시 `Authorization` 헤더로만 전달합니다.
- API mock 데이터는 실제 API 연결 전 임시로만 사용하고, 위치와 제거 계획을 README 또는 TODO에 남깁니다.

## 충돌 방지

- 팀장이 제공하는 AI 생성 UI 파일은 `frontend/ui-drop/`에 먼저 둡니다.
- 실제 앱 구조로 옮길 때 파일명을 기능 단위로 정리합니다.
- API 응답 타입은 `contracts/api/openapi.yaml`과 맞춥니다.
- 백엔드 endpoint 변경이 필요하면 프론트에서 임의로 계약을 바꾸지 말고 PR/이슈로 요청합니다.
