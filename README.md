# Farm하니? 🌱

> 식물 사진과 재배일지를 입력하면 공식 원예·농업 자료를 근거로 현재 상태와 오늘의 관리 행동을 알려주는 **멀티모달 RAG 기반 식물 주치의 AI**

![Farm하니? 메인 대시보드](docs/assets/dashboard.png)

*Farm하니? 메인 대시보드 — 내 식물 카드 · 건강 개요 · 빠른 AI 진단*

https://farmhani.vercel.app/ (OpenAPI 07/12까지 지원 예정)

---

## 팀원 소개

**SKN30 3차 단위 프로젝트 · 3팀**

| 이름 | 역할 | 주요 담당 |
|---|---|---|
| **채동현** | 총괄 팀장 · 프론트 | 프로젝트 총괄 및 일정 관리, 프론트엔드 UI 설계·구현, 데이터 수집 파이프라인 구축, 서비스 통합 구현 및 배포 |
| **강성준** | 백엔드 · RAG | LangGraph 기반 RAG 답변 파이프라인 설계·구현, Supabase 서버 구축 |
| **남태식** | 백엔드 · RAG | LangGraph 기반 RAG 답변 파이프라인 설계·구현, Supabase 서버 구축 |
| **김도훈** | 데이터 | 데이터 수집 파이프라인 구현 및 전처리, RAG 데이터 적재 |
| **김범중** | 데이터 | 데이터 수집 파이프라인 구현 및 전처리, RAG 데이터 적재 |

---

## 서비스 소개

사용자가 등록한 식물 프로필, 재배일지, 사진을 바탕으로 AI가 현재 상태를 진단하고 맞춤 관리 가이드를 제공합니다.
병명 확정 진단 대신 **공식 농업·원예 자료를 근거로 의심 상태와 오늘 할 일**을 안내하는 것이 핵심 원칙입니다.

기존 농업 플랫폼의 병해충 상담은 이웃 문답형 커뮤니티에 가까워 답변까지 오래 걸리고 정확성 검증이 어렵습니다.
Farm하니는 **공식 문서 기반 RAG가 내 식물의 기록·사진과 결합해 즉시, 출처와 함께 답변**하는 방식으로 이 한계를 해결합니다.

### 주요 기능

| 기능 | 설명 |
|---|---|
| 식물 프로필 관리 | 식물명·품종·위치 등록, 사진 업로드, 재배일지 작성 |
| 전문가 상담 모드 | 객관적·전문적 말투로 상태 분석 및 관리 가이드 제공 |
| 내 식물과 대화 모드 | 식물이 1인칭으로 말하는 친근한 대화형 모드 |
| RAG 근거 제공 | 답변마다 참조한 공식 문서 출처(citations) 표시 |
| 멀티모달 이미지 분석 | 식물 사진에서 이상 신호 자동 추출 (GPT-4o-mini Vision) |

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React + TypeScript + Vite (해시 라우팅, 디자인 HTML 주입 구조) |
| Backend | FastAPI + Pydantic (Python 3.11+) |
| AI / LLM | OpenAI GPT-4o-mini (채팅·Vision), text-embedding-3-small (임베딩, 1536차원) |
| RAG 워크플로우 | LangGraph StateGraph — 10단계 에이전틱 파이프라인 |
| DB / Auth / Vector / Storage | Supabase (PostgreSQL + pgvector + Auth + Storage) |
| 배포 | Vercel (Frontend) · Render (Backend) · Supabase — **전 구간 실배포 완료** |

---

## RAG 파이프라인 — LangGraph 10단계

<img src="docs/assets/langgraph_flow.png" alt="LangGraph StateGraph 10단계 파이프라인" width="360" align="right" />

단순 1회성 벡터 검색이 아니라, 입력 검증부터 멀티모달 신호 병합, 동적 쿼리 생성, 문서 필터링, 안전성 검토까지 이어지는 **에이전틱 워크플로우**입니다.

**입력 이해 (1~4단계)**
식물·일지·사진 검증 → 최근 12개 대화 로드 → Vision 이상 신호 추출 → 사용자 맥락 요약

**검색 (5~6단계)**
LLM 쿼리 확장(3개 생성) → pgvector 유사도 + 키워드 하이브리드 검색(RRF 병합).
임계값을 완화(0.32→0.25)해 후보 문서를 폭넓게 수집 — *Recall 확보*

**검증·필터링 (7단계) — 핵심**
`grade_or_rerank`: LLM이 후보 문서를 하나씩 읽고 질문 식물종과 일치하는지 검증.
무관한 문서를 엄격히 탈락시켜 환각을 원천 차단 — *Precision 확보*

**생성·안전 (8~9단계)**
전문가 / 반려식물 1인칭 모드에 맞춘 답변 생성 + 출처 바인딩.
`safety_review`가 농약 관련 답변에 안전 고지를 강제 조립

**영속화 (10단계)**
답변·출처·세션 제목을 Supabase에 저장 — 식물별 상담 이력 보존

<br clear="right" />

---

## RAG 품질 개선 및 평가

**LLM-as-a-Judge 자동 평가 프레임워크**(gpt-4o-mini Judge, 12개 골든셋)를 구축하고, 이를 기반으로 검색 품질을 정량 추적하며 개선했습니다.

![RAG 평가 지표 개선 전후 비교](docs/assets/rag_eval_chart.png)

### 핵심 개선 기법

- **Two-Stage Retrieval**: 임계값 0.32→0.25 완화로 Recall 확보 후, `grade_or_rerank`로 Precision 정제
- **한국어 조사 제거 휴리스틱**: "몬스테라는" → "몬스테라" 추출로 키워드 매칭 노이즈 제거
- **RRF 하이브리드 병합**: 벡터 + 키워드 검색 결과를 Reciprocal Rank Fusion으로 재정렬
- **LLM 쿼리 확장**: 식물 품종·관찰 징후·최근 이력을 종합한 검색 쿼리 3개 자동 생성
- **환각 방지**: 근거 문서가 없으면 "모른다"를 선언 — 무관 문서 강제 주입 로직 제거

> 검색 정확도 **3.58 → 4.83점** 대폭 개선, 사진 반영 **만점(5.00)** 달성

---

## 데이터 파이프라인

공공·공식 데이터 소스에서 수집해 Supabase pgvector에 **총 1,682건의 청크**를 통합 적재했습니다.

| 출처 | 내용 | 적재량 |
|---|---|---:|
| 농사로 | 작목정보·전자책·농작업일정·주간농사정보·실내식물 | 711건 |
| NCPMS 병해충 | 병·해충 발생조건, 증상, 예방 (OpenAPI) | 479건 |
| AI Hub | 농축수산 목록·화훼 물주기·육묘 생장 | 143건 |
| 국립수목원 도감 | 식물 특징·학명·과명 — 실내·관상·작물 | 100건 |
| PSIS 농약 정보 | 농약등록정보 — 안전 참고 전용 | 100건 |
| 농업날씨365 · 네이버 지식백과 | 기상 컨텍스트 + 식물 보조 문서 | 149건 |

### 전처리 파이프라인

```
수집 (공공 API·CSV·HWPX) → JSONL 정규화 → 클렌징 (HTML·공백 제거)
→ 식물명 메타 태깅 → 청킹 (출처별 가변) → 임베딩 (1536차원) → Supabase pgvector 적재
```

**출처별 가변 청킹 전략**

| 대상 | 파라미터 | 근거 |
|---|---|---|
| 기본값 (HWPX 작업일정 등) | 2200자 / overlap 250자 | 표·문단 재구성 문서 — 일정 흐름 맥락 보존 |
| NCPMS 병해충 문서 | 1400자 / overlap 160자 | 증상·발생조건·예방이 짧고 밀도 높음 |
| 농사로 실내식물·작물 | 1200자 / overlap 140자 | 물주기·광도 등 항목형 정보에 최적 |

- `category`로 문서 성격 구분, `usage_scope`로 RAG 사용 범위 제어 (`rag` / `reference_only` / `safety_reference_only`)
- 자동 정합성 검증(`validate_processed_data.py`) **PASS** — UUID 고유성, FK 연결, 벡터 차원, 안전 태그 주입 검증

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

## Supabase 테이블 구조

| 테이블 | 역할 |
|---|---|
| `plants` / `care_logs` / `plant_photos` | 사용자 식물 프로필 · 재배일지 · 사진 |
| `chat_sessions` / `chat_messages` | 채팅 세션 · 메시지 이력 |
| `rag_chunks` / `rag_sources` | RAG 문서 청크(pgvector) · 소스 메타데이터 |
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
├── docs/                      # 아키텍처·전처리·RAG 품질 보고서, 발표자료
│   └── assets/                # README 이미지 자산
├── frontend/                  # React + TypeScript + Vite
│   └── src/
│       ├── App.tsx            # 메인 앱 (해시 라우팅)
│       ├── api.ts             # 백엔드 API 호출
│       └── types.ts           # 타입 정의
├── backend/                   # FastAPI + LangGraph
│   └── app/
│       ├── main.py            # 앱 진입점
│       ├── api/v1/            # API 라우터
│       ├── services/rag/      # RAG 파이프라인 (pipeline·vectorstore·vision)
│       ├── auth/              # Supabase JWT 인증
│       └── schemas/           # Pydantic 스키마
├── data/
│   ├── raw / interim / processed / vectorstore   # 단계별 데이터 산출물
│   └── scripts/               # 수집·정규화·청킹·임베딩·적재 스크립트
└── server/                    # Docker, 배포 설정
```

---

## 로컬 실행

```bash
# 환경변수
cp .env.example .env   # Supabase URL/Key, OpenAI API Key 등 입력

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

---

## 현재의 한계와 확장 계획

**한계**

- 방대한 식물 종 대비 데이터 수집이 아직 완전하지 않음 — 문서가 없는 식물은 상담 근거 부족
- RAG 검색이 완벽하다고 말하기는 어려움 — 무정보 상황의 거절 패턴 등 지속 고도화 필요

**확장 계획**

- 소규모 반려식물 → **대규모 농사·전문 관리 도메인**으로 확장
- PSIS 농약등록정보 100건 선제 수집 완료 — 현재는 안전 참고 전용이지만, `usage_scope` 설계 덕분에 데이터 재수집 없이 정책 변경만으로 전문 방제 가이드(적용 약제·안전 희석 배수) 기능으로 확장 가능
- 물주기 자동 리마인드·모바일 알림, 이미지 진단 정확도 고도화

---

## 보안 원칙

- `.env`, API 키, Supabase service role key는 Git에 커밋하지 않습니다.
- 사용자별 데이터는 Supabase JWT 인증으로 분리하고, service role key는 백엔드에서만 사용합니다.
- 병해충·농약 관련 답변은 확정 진단·직접 처방 표현을 사용하지 않습니다.
- RAG 답변은 반드시 출처 메타데이터를 포함합니다.
