# API Contract 운영 규칙

프론트와 백엔드는 `contracts/api/openapi.yaml`을 기준으로 맞춥니다. 실제 구현 전이라도 화면과 API가 동시에 진행될 수 있도록 요청/응답 구조를 먼저 합의합니다.

## 변경 절차

1. Backend 담당자가 endpoint, request, response, error schema를 수정합니다.
2. Frontend 담당자가 UI 영향 범위를 확인합니다.
3. 팀장이 breaking change 여부를 확인합니다.
4. PR 설명에 변경된 endpoint와 필요한 UI 수정 사항을 적습니다.

## 인증 기준

- 로그인/로그아웃은 Supabase Auth가 담당합니다.
- Frontend는 access token을 Backend API 요청의 `Authorization: Bearer <token>` 헤더로 보냅니다.
- Backend는 JWT를 검증하고 `user_id`를 서버에서 확정합니다.
- request body에서 받은 `user_id`를 신뢰하지 않습니다.

## 에러 응답 원칙

- `401`: 로그인 필요 또는 token 만료
- `403`: 다른 사용자의 식물/사진/상담 접근
- `404`: 리소스 없음
- `422`: 입력값 검증 실패
- `500`: 서버 내부 오류

## 버전 관리

초기 API는 `/api/v1` prefix를 사용합니다. 큰 변경이 생기면 v2를 추가하고 v1을 즉시 삭제하지 않습니다.
