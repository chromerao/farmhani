# Agent 작업 지침서

이 repo는 여러 팀원이 각자 Agent를 연결해서 동시에 작업하는 것을 전제로 합니다. 모든 Agent는 이 파일과 담당 폴더의 `AGENTS.md`를 먼저 읽고, 담당 영역 밖의 변경을 최소화해야 합니다.

## 절대 규칙

1. 비밀값을 커밋하지 않습니다. `.env`, API Key, Supabase service role key, DB password, 개인 토큰은 Git에 올리지 않습니다.
2. 원본 대용량 데이터와 사용자 업로드 파일을 커밋하지 않습니다. AI Hub 원본, 이미지 원본, 벡터 DB 파일, 모델 weight는 Git 외부 저장소를 사용합니다.
3. 담당 폴더 밖의 파일은 사전 합의 없이 수정하지 않습니다.
4. `main` 브랜치에 직접 커밋하지 않습니다. 기능별 브랜치에서 PR로 병합합니다.
5. 충돌 해결을 위해 `git reset --hard`, 강제 push, 다른 사람 변경 삭제를 하지 않습니다.
6. RAG 답변은 출처를 남기고, 병명 확정/농약 직접 처방처럼 보이는 문구를 피합니다.

## 권장 브랜치 규칙

- `feature/frontend-작업명`
- `feature/backend-작업명`
- `feature/data-작업명`
- `feature/server-작업명`
- `docs/작업명`
- Agent가 자동 브랜치를 만들 때는 `codex/작업명`도 허용합니다.

## 폴더 소유권

| 폴더/파일 | 주 담당 | 수정 규칙 |
|---|---|---|
| `frontend/` | 프론트 담당/팀장 | UI와 API 연결 작업. 백엔드 로직을 만들지 않습니다. |
| `backend/` | 백엔드 담당 | FastAPI, LangGraph, 인증 검증, DB 모델. 프론트 UI를 수정하지 않습니다. |
| `data/` | 데이터 담당 | 수집/전처리/청킹/메타데이터. API 서버 코드를 수정하지 않습니다. |
| `server/` | 서버/배포 담당 | Docker, 배포, CI/CD, 운영 설정. 앱 로직 변경은 담당자와 합의합니다. |
| `contracts/` | 백엔드 담당 + 팀장 승인 | 프론트/백엔드 공유 계약입니다. 변경 시 README 또는 PR 설명에 영향 범위를 씁니다. |
| `docs/` | 팀장 중심, 전원 가능 | 설계 문서입니다. 사실과 맞지 않는 오래된 내용은 함께 갱신합니다. |
| `.env.example` | 서버/백엔드 담당 + 팀장 승인 | 새 환경변수가 생길 때만 추가합니다. 실제 값 금지. |
| `README.md`, `AGENTS.md` | 팀장 승인 | 프로젝트 전체 규칙이므로 임의 변경하지 않습니다. |

## 공유 파일 변경 프로토콜

다음 파일은 충돌 위험이 높으므로 단독으로 크게 바꾸지 않습니다.

- `README.md`
- `AGENTS.md`
- `.env.example`
- `contracts/api/openapi.yaml`
- `docs/architecture.md`
- 배포 설정 파일
- dependency lock 파일

공유 파일을 바꿀 때는 PR 설명에 다음을 적습니다.

- 왜 변경했는지
- 영향을 받는 파트
- 프론트/백엔드/API 계약 변경 여부
- 필요한 환경변수 추가 여부

## Frontend Agent 규칙

- 작업 범위: `frontend/`, 필요 시 `contracts/` 읽기 전용.
- 팀장이 AI로 만든 UI 파일은 먼저 `frontend/ui-drop/`에 보관하고, 실제 앱 구조에 맞게 정리한 뒤 반영합니다.
- API URL, Supabase URL, public anon key는 환경변수로만 사용합니다.
- service role key나 서버 전용 secret을 프론트 코드에 넣지 않습니다.
- 로그인/로그아웃은 Supabase Auth 또는 확정된 Auth Provider SDK를 사용합니다.
- API 요청/응답 타입은 `contracts/api/openapi.yaml`을 기준으로 맞춥니다.

## Backend Agent 규칙

- 작업 범위: `backend/`, `contracts/api/`, 필요 시 `docs/rag-langgraph.md`.
- FastAPI + Pydantic 기준으로 요청/응답 schema를 명확히 둡니다.
- 모든 사용자 데이터 API는 Supabase JWT 검증 후 `user_id` 기준으로 접근을 제한합니다.
- RAG 답변에는 검색된 문서의 출처, 제목, URL 또는 source id를 포함합니다.
- LangGraph 노드는 입력 정리, 이미지 신호 추출, 검색, 답변 생성, 안전성 검토, 저장을 분리합니다.
- 테스트는 최소한 인증 실패, 정상 요청, RAG fallback, 출처 포함 여부를 다룹니다.

## Data Agent 규칙

- 작업 범위: `data/`.
- `data/raw/`, `data/external/`, `data/vectorstore/`에는 실제 데이터 파일을 커밋하지 않습니다.
- 수집한 자료는 `data/catalog/`에 출처, 라이선스, 수집일, 사용 목적, 담당자를 기록합니다.
- 전처리 산출물은 재현 가능한 script로 생성합니다.
- RAG용 문서는 chunk id, source id, title, url, collected_at, license, category 메타데이터를 포함해야 합니다.
- 병해충/농약 데이터는 사용자에게 확정 처방으로 노출되지 않도록 주의 문구와 함께 태깅합니다.

## Server Agent 규칙

- 작업 범위: `server/`, `.env.example`, 배포 관련 문서.
- Dockerfile, compose, 배포 스크립트에 secret을 하드코딩하지 않습니다.
- 로컬/스테이징/프로덕션 환경변수를 분리합니다.
- 배포 환경에는 health check, 로그 확인 방법, rollback 방법을 문서화합니다.
- Supabase, Render/Railway/Fly.io, Vercel 설정 변경은 문서에 남깁니다.

## RAG/LangGraph 안전 기준

- 답변은 "가능성", "의심", "관찰 필요" 중심으로 표현합니다.
- 농약/방제 내용은 전문가 확인, 라벨 확인, 안전사용기준 준수를 함께 안내합니다.
- 검색 결과가 부족하면 모르는 것을 명시하고 추가 사진/기록을 요청합니다.
- 사용자 업로드 이미지는 동의 없이 학습 데이터로 재사용하지 않습니다.

## PR 체크리스트

- 담당 폴더 밖 변경이 있는지 확인했습니다.
- secret, 원본 데이터, 캐시, 로그 파일이 포함되지 않았습니다.
- README 또는 담당 폴더 문서가 필요한 만큼 갱신되었습니다.
- API 계약 변경 시 `contracts/api/openapi.yaml`과 프론트/백엔드 사용처를 함께 확인했습니다.
- 실행 가능한 테스트 또는 수동 검증 결과를 PR에 적었습니다.
