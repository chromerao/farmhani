# Farm하니? 🌱

> 식물 사진과 재배일지를 입력하면 공식 원예·농업 자료를 근거로 현재 상태와 오늘의 관리 행동을 알려주는 **멀티모달 RAG 기반 식물 케어 챗봇**

---

## 서비스 소개

사용자가 등록한 식물 프로필, 재배일지, 사진을 바탕으로 AI가 현재 상태를 진단하고 맞춤 관리 가이드를 제공합니다.  
병명 확정 진단 대신 **공식 농업·원예 자료를 근거로 의심 상태와 오늘 할 일**을 안내하는 것이 핵심 원칙입니다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 식물 프로필 관리 | 식물명·품종·위치 등록, 사진 업로드, 재배일지 작성 |
| 전문가 상담 모드 | 객관적·전문적 말투로 상태 분석 및 관리 가이드 제공 |
| 내 식물과 대화 모드 | 식물이 1인칭으로 말하는 친근한 대화형 모드 |
| RAG 근거 제공 | 답변마다 참조한 공식 문서 출처 표시 |
| 멀티모달 이미지 분석 | 식물 사진에서 이상 신호 자동 추출 (GPT-4o-mini Vision) |

---

## 기술 스택

### Backend
| 항목 | 선택 |
|---|---|
| 프레임워크 | FastAPI (Python 3.11+) |
| AI/LLM | OpenAI GPT-4o-mini (채팅·비전), text-embedding-3-small (임베딩) |
| RAG 워크플로우 | LangGraph StateGraph (10단계 파이프라인) |
| DB / Auth | Supabase (PostgreSQL + pgvector + Auth) |
| 실행 서버 | uvicorn |

### Frontend
| 항목 | 선택 |
|---|---|
| 프레임워크 | React + TypeScript + Vite |
| 라우팅 | Hash 기반 (`#login` / `#dashboard` / `#add` / `#detail` / `#chat`) |
| UI 방식 | 정적 HTML 디자인 파일을 동적으로 주입하는 하이브리드 구조 |

### 배포
| 파트 | 서비스 |
|---|---|
| Frontend | Vercel |
| Backend API | Render / Railway |
| DB / Auth / Vector | Supabase |
| 사진 스토리지 | Supabase Storage |

---

## RAG 파이프라인 (LangGraph 10단계)

```
1. validate_input        → 식물·일지·사진 DB 조회
2. load_chat_history     → 이전 대화 로드 (최근 12개)
3. extract_image_signals → 이미지 비전 분석 + 이상 신호 키워드 추출
4. summarize_user_context→ 식물 컨텍스트 문자열 생성
5. build_retrieval_query → OpenAI로 검색 쿼리 3개 생성
6. retrieve_docs         → 벡터 검색 (top_k=8, RRF 병합)
7. grade_or_rerank       → LLM 기반 문서 적합성 필터링
8. generate_answer       → GPT-4o-mini 구조화 답변 생성
9. safety_review         → 안전 고지 추가
10. persist_result       → Supabase 세션·메시지 저장
```

**벡터 검색 우선순위:**
1. OpenAI 임베딩 + Supabase pgvector RPC `match_rag_chunks` (유사도 임계값 0.32)
2. Supabase 키워드 스캔 (최대 3,000행)
3. 로컬 JSON fallback (`data/processed/gardening_docs.json`)

---

## 데이터 소스

| 출처 | 내용 |
|---|---|
| AI Hub 원예·육묘 데이터셋 | 시설·노지 작물 생육 데이터 |
| NCPMS 병해충 데이터 | 토마토·상추·고추 병해충 및 해충 정보 |
| 농사로 (Nongsaro) | 정원·실내식물 관리 가이드 |
| 국립원예특작과학원 | 실내정원 유지관리 자료 |

---

## 주요 API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 확인 |
| GET | `/api/v1/plants` | 사용자 식물 목록 조회 |
| POST | `/api/v1/plants` | 식물 프로필 등록 |
| POST | `/api/v1/plants/{id}/care-logs` | 재배일지 추가 |
| POST | `/api/v1/plants/{id}/photos` | 식물 사진 업로드 |
| POST | `/api/v1/chat/plant-care` | RAG 기반 식물 케어 상담 |
| GET | `/api/v1/plant-catalog` | 식물 품종 도감 조회·검색 |
| GET | `/docs` | Swagger UI (API 문서) |

---

## Supabase 테이블 구조

| 테이블 | 역할 |
|---|---|
| `plants` | 사용자 식물 프로필 |
| `care_logs` | 재배 일지 |
| `plant_photos` | 식물 사진 참조 |
| `chat_sessions` | 채팅 세션 |
| `chat_messages` | 채팅 메시지 이력 |
| `rag_chunks` | RAG 문서 청크 (pgvector) |
| `rag_sources` | RAG 소스 메타데이터 |
| `plant_catalog` | 식물 품종 도감 |

---

## 프로젝트 구조

```text
.
├── README.md
├── AGENTS.md                  # Agent 협업 규칙
├── .env.example               # 환경변수 템플릿
├── vercel.json                # Vercel 프론트 배포 설정
├── contracts/
│   └── api/openapi.yaml       # 프론트-백엔드 API 계약
├── docs/
│   ├── architecture.md
│   ├── rag-langgraph.md
│   ├── deployment.md
│   └── api-contract.md
├── frontend/                  # React + TypeScript + Vite
│   └── src/
│       ├── App.tsx            # 메인 앱 (해시 라우팅)
│       ├── api.ts             # 백엔드 API 호출
│       └── types.ts           # 타입 정의
├── backend/                   # FastAPI + LangGraph
│   └── app/
│       ├── main.py            # 앱 진입점
│       ├── api/v1/            # API 라우터
│       ├── services/rag/      # RAG 파이프라인
│       │   ├── pipeline.py
│       │   ├── vectorstore.py
│       │   └── vision.py
│       ├── auth/              # Supabase JWT 인증
│       ├── db/                # DB 세션
│       └── schemas/           # Pydantic 스키마
├── data/
│   ├── interim/               # 수집·전처리 원본 데이터
│   └── processed/             # RAG 인덱싱용 최종 청크
└── server/                    # Docker, 배포 설정
```

---

## 로컬 실행

### 환경변수 설정

```bash
cp .env.example .env
# .env에 Supabase URL/Key, OpenAI API Key 등 입력
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

---

## 팀 구성

| 역할 | 주요 담당 |
|---|---|
| 총괄 팀장 | 일정·범위, API 계약 승인, 프론트 UI 통합 |
| 데이터 수집·전처리 (2명) | 공식 문서 수집, 정제, 청킹, 벡터 인덱싱 |
| 백엔드·API | FastAPI, RAG/LangGraph, DB 모델, Supabase 연동 |
| 서버·배포 | Docker, Vercel/Render 배포, 환경변수 관리 |

---

## 보안 원칙

- `.env`, API 키, Supabase service role key는 Git에 커밋하지 않습니다.
- 사용자별 데이터는 Supabase JWT 인증으로 분리합니다.
- 병해충·농약 관련 답변은 확정 진단·직접 처방 표현을 사용하지 않습니다.
- RAG 답변은 반드시 출처 메타데이터를 포함합니다.
