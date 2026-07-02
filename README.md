# 서비스 제목 : Farm하니?

식물 사진과 재배일지를 입력하면 공식 원예/농업 자료를 근거로 현재 상태와 오늘의 관리 행동을 알려주는 멀티모달 RAG 기반 식물 케어 챗봇입니다.

## 1차 MVP

- 대상: 실내식물 + 텃밭/작물 일부
- 입력: 식물명, 사진, 최근 물 준 날짜, 햇빛 위치, 잎 상태, 재배일지
- 출력: 현재 상태 요약, 원인 후보, 오늘 할 일, 추가 관찰 포인트, 근거 문서
- 원칙: 병명 확정 진단이 아니라 공식 자료 기반의 의심 상태와 관리 가이드를 제공합니다.

## 팀 역할

| 역할 | 인원 | 주 책임 | 주요 폴더 |
|---|---:|---|---|
| 총괄 팀장 | 1 | 일정/범위 결정, API 계약 승인, 프론트 UI 파일 반영, PR 최종 리뷰 | `README.md`, `AGENTS.md`, `docs/`, `contracts/`, `frontend/ui-drop/` |
| 데이터 수집/전처리 | 2 | 공식 문서/API 수집, 정제, 청킹, 메타데이터, 벡터 인덱스 입력물 생성 | `data/` |
| 백엔드/API | 1 | FastAPI, 인증 검증, RAG/LangGraph API, DB 모델, 테스트 | `backend/`, `contracts/api/` |
| 서버/배포 | 1 | Docker, 배포 환경, CI/CD, 환경변수, 운영 체크리스트 | `server/`, `.env.example`, `docs/deployment.md` |
| 프론트엔드 | 팀장+AI 산출물 | UI 구현/통합, 로그인/로그아웃 화면, API 연결 | `frontend/` |

## Workspace 구조

```text
.
├── AGENTS.md                  # 모든 Agent가 따라야 하는 협업/보안 규칙
├── README.md                  # 프로젝트 개요와 작업 기준
├── .env.example               # 환경변수 템플릿, 실제 비밀값 금지
├── .gitignore                 # 대용량 데이터/비밀값/캐시 제외
├── contracts/
│   └── api/openapi.yaml       # 프론트-백엔드 공유 API 계약
├── docs/
│   ├── architecture.md        # 전체 아키텍처
│   ├── api-contract.md        # API 계약 운영 규칙
│   ├── deployment.md          # 배포 서비스 추천과 환경 분리
│   └── rag-langgraph.md       # RAG/LangGraph 설계
├── frontend/                  # UI 앱과 AI 생성 UI 파일 반영 영역
├── backend/                   # API 서버, 인증 검증, RAG/LangGraph 실행
├── data/                      # 데이터 수집, 전처리, 청킹, 인덱싱 산출물
└── server/                    # Docker, 배포 설정, 운영 스크립트
```

## 권장 기술 스택

| 영역 | 권장 선택 | 이유 |
|---|---|---|
| Frontend | Next.js 또는 React + TypeScript | AI가 만든 UI 파일 반영이 쉽고 Vercel 배포/프리뷰가 편합니다. |
| Backend | FastAPI + Pydantic + LangGraph | Python RAG 파이프라인과 API 서버를 한 코드베이스에서 관리하기 좋습니다. |
| Auth/DB/Vector | Supabase Auth + Postgres + pgvector | 로그인/로그아웃, 사용자별 데이터, 벡터 검색을 MVP에서 한 번에 처리할 수 있습니다. |
| Object Storage | Supabase Storage 또는 Cloudflare R2 | 사용자 식물 사진과 원문 문서 파일을 Git 밖에서 관리합니다. |
| RAG | LangChain document loader/splitter + pgvector | 공식 문서 기반 검색, 출처 메타데이터, 향후 확장이 쉽습니다. |
| Workflow | LangGraph | 이미지 분석, 문서 검색, 답변 생성, 안전성 검토를 노드 단위로 분리합니다. |
| Observability | LangSmith 선택 적용 | RAG 검색 품질과 LangGraph 실행 경로를 추적할 수 있습니다. |

## 배포 추천

- Frontend: Vercel을 1순위로 추천합니다. PR 단위 프리뷰 배포가 쉬워 UI 검수가 빠릅니다.
- Backend/RAG API: Render, Railway, Fly.io 중 하나를 추천합니다. MVP는 Render 또는 Railway가 단순합니다.
- Database/Auth/Vector: Supabase를 추천합니다. Auth, Postgres, pgvector, Storage를 함께 쓸 수 있습니다.
- Server/Infra: Docker Compose로 로컬 실행을 통일하고, 운영 배포 설정은 `server/`에 모읍니다.
- 도메인/DNS: Cloudflare를 사용하면 DNS, HTTPS, 캐시, 추후 R2 연동이 편합니다.

## 핵심 기능 설계

1. 사용자는 로그인 후 식물 프로필을 등록합니다.
2. 사진, 물 준 날짜, 햇빛 위치, 잎 상태, 재배일지를 입력합니다.
3. Backend가 Supabase JWT를 검증하고 사용자별 데이터 접근을 제한합니다.
4. LangGraph가 입력 정리, 이미지 이상 신호 추출, RAG 검색, 답변 생성, 안전성 검토를 순서대로 실행합니다.
5. 답변은 현재 상태 요약, 원인 후보, 오늘 할 일, 관찰 체크리스트, 근거 문서를 포함합니다.

## 공식 데이터 우선순위

- 1순위: 농사로 실내식물 물관리, 국립원예특작과학원 실내정원 유지관리 자료
- 2순위: 농촌진흥청 작목별 농업기술정보, 주간농사정보 OpenAPI
- 3순위: 도시농업 병해충 관리, 병해충 예찰정보 API
- 4순위: AI Hub 시설/노지 작물 질병 이미지 일부
- 2차 확장: 농업기상, 스마트팜 우수농가 공개 데이터, 농약안전사용지침 API

## 협업 기본 규칙

- 모든 Agent는 작업 전 `AGENTS.md`와 담당 폴더의 `AGENTS.md`를 먼저 읽습니다.
- 각자 담당 폴더 밖의 파일은 팀장 또는 해당 파트 담당자와 합의한 경우만 수정합니다.
- `.env`, API Key, Supabase service role key, 원본 대용량 데이터, 사용자 업로드 이미지는 Git에 커밋하지 않습니다.
- 프론트와 백엔드는 `contracts/api/openapi.yaml`을 기준으로 맞춥니다.
- RAG 답변은 반드시 출처 메타데이터를 포함하고, 병해충/농약 관련 내용은 확정 진단이나 직접 처방처럼 표현하지 않습니다.

## 로컬 개발 예정 흐름

초기 스캐폴딩 후 아래 형태로 통일합니다.

```bash
# frontend
cd frontend
npm install
npm run dev

# backend
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

현재 repo는 구조 설계 단계입니다. 실제 앱 스캐폴딩이 들어오면 각 파트 README의 실행 명령을 최신화하세요.
