# Backend Agent 지침

## 작업 범위

- 수정 가능: `backend/`, `contracts/api/`
- 읽기 권장: `docs/rag-langgraph.md`, `docs/architecture.md`, `data/catalog/`
- 수정 전 합의 필요: `frontend/`, `server/`, root 문서

## 책임

- FastAPI 서버
- Supabase JWT 검증
- 사용자별 식물/재배일지/사진/상담 API
- LangGraph workflow 실행
- RAG 검색 및 citation 포함 답변
- DB schema/migration
- backend test

## 보안 규칙

- request body의 `user_id`를 신뢰하지 않습니다.
- JWT에서 확정한 사용자만 자신의 데이터에 접근할 수 있습니다.
- service role key는 backend/server 환경에서만 사용합니다.
- user upload URL, signed URL, log에 민감 정보가 남지 않게 합니다.

## RAG 구현 규칙

- 답변에는 최소한 source id, title, publisher 또는 URL을 포함합니다.
- 검색 결과가 부족하면 fallback 답변과 추가 질문을 반환합니다.
- 확정 진단, 농약 직접 처방, 과장 표현은 `safety_review` 단계에서 제거합니다.
- LangGraph 노드는 작게 분리하고, 각 노드 입력/출력 타입을 명확히 둡니다.

## 테스트 기준

- `/health`
- 인증 없음/만료 token
- 다른 사용자의 plant 접근 차단
- 정상 plant/care-log 생성
- RAG 응답에 citations 포함
- 검색 결과 부족 시 fallback
