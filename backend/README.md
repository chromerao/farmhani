# Backend

FastAPI 기반 API 서버와 LangGraph/RAG 실행 영역입니다.

## 권장 스택

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy 또는 Supabase Python client
- LangGraph + LangChain
- pgvector
- pytest

## 예정 구조

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── auth/
│   ├── core/
│   ├── db/
│   ├── rag/
│   ├── graphs/
│   └── schemas/
├── migrations/
└── tests/
```

## 핵심 API

- `GET /health`
- `GET /api/v1/plants`
- `POST /api/v1/plants`
- `POST /api/v1/plants/{plantId}/care-logs`
- `POST /api/v1/plants/{plantId}/photos`
- `POST /api/v1/chat/plant-care`

상세 계약은 `contracts/api/openapi.yaml`을 기준으로 합니다.

## Frontend 연동 규격

현재 프론트엔드는 `frontend/design/*.html` 원본 시안을 보존하는 방식으로 구현되어 있습니다. Backend는 화면 디자인을 직접 수정하지 않고, 아래 API 계약을 안정적으로 제공하는 데 집중합니다.

### 실행 기준

- Frontend dev URL: `http://localhost:3000` 또는 `http://127.0.0.1:3000`
- Backend dev URL: `http://localhost:8000`
- Frontend 환경변수: `VITE_BACKEND_URL=http://localhost:8000`
- Backend CORS 허용값은 root `.env.example`의 `CORS_ORIGINS` 기준으로 설정합니다.

### 프론트가 기대하는 우선 API

1차 통합에서 프론트가 먼저 붙을 API는 아래 순서입니다.

1. `GET /api/v1/plants`
2. `POST /api/v1/plants`
3. `POST /api/v1/plants/{plantId}/care-logs`
4. `POST /api/v1/plants/{plantId}/photos`
5. `POST /api/v1/chat/plant-care`

곧 추가가 필요한 API 후보:

- `GET /api/v1/plant-catalog`: 식물 등록 화면의 품종 검색/자동완성
- `POST /api/v1/uploads/signed-url`: Supabase Storage 사진 업로드용 signed URL 발급

### 필드 이름 규칙

프론트와 계약한 JSON 필드는 camelCase를 사용합니다.

- `createdAt`
- `wateredAt`
- `leafCondition`
- `soilCondition`
- `storagePath`
- `capturedAt`
- `possibleCauses`
- `todayActions`
- `observationChecklist`
- `safetyNotice`
- `sourceId`

Python 내부 모델에서 snake_case를 쓰더라도 API 응답은 `contracts/api/openapi.yaml`의 camelCase를 유지합니다.

### 필수 응답 형태

`GET /api/v1/plants`는 최소 아래 필드를 반환해야 합니다.

```json
[
  {
    "id": "d3b07384-d113-49c3-a558-1ec114a84d41",
    "name": "몬스테라",
    "species": "Monstera deliciosa",
    "location": "거실 창가",
    "sunlight": "밝은 간접광",
    "createdAt": "2026-06-30T00:00:00Z"
  }
]
```

`POST /api/v1/chat/plant-care`는 최소 아래 필드를 반환해야 합니다.

```json
{
  "summary": "현재 상태 요약",
  "possibleCauses": ["원인 후보 1", "원인 후보 2"],
  "todayActions": ["오늘 할 일 1", "오늘 할 일 2"],
  "observationChecklist": ["추가 관찰 포인트 1"],
  "citations": [
    {
      "sourceId": "nongsaro_indoor_water",
      "title": "농사로 실내식물 물관리 자료",
      "url": "https://www.nongsaro.go.kr/",
      "publisher": "농촌진흥청/농사로"
    }
  ],
  "safetyNotice": "본 결과는 참고용 관리 가이드이며 확정 진단이 아닙니다."
}
```

### 인증 연동 기준

- Supabase Auth를 사용합니다.
- 프론트는 로그인 후 Supabase access token을 `Authorization: Bearer <token>`으로 전달합니다.
- Backend는 request body의 `user_id`를 신뢰하지 않습니다.
- Backend는 JWT 검증 결과에서 사용자 식별자를 확정하고, 해당 사용자 데이터만 조회/수정합니다.
- 개발 초기 mock API는 인증 없이 허용할 수 있지만, 실제 DB 연결 시점부터 인증 검증을 추가합니다.

### 사진 업로드 기준

- 프론트가 직접 Backend로 이미지 바이너리를 보내는 방식은 1차 기본안이 아닙니다.
- 권장 흐름:
  1. Frontend가 Backend에 signed upload URL 요청
  2. Backend가 Supabase Storage 경로와 signed URL 발급
  3. Frontend가 Supabase Storage에 직접 업로드
  4. Frontend가 `POST /api/v1/plants/{plantId}/photos`로 `storagePath` 메타데이터 등록
- Storage bucket 기본값은 root `.env.example`의 `SUPABASE_STORAGE_BUCKET=plant-photos`입니다.

### RAG 답변 안전 기준

- `citations`는 빈 배열이면 안 됩니다. 검색 결과가 부족하면 fallback source 또는 "추가 정보 필요" 상태를 명확히 반환합니다.
- 병해충/농약 관련 응답은 확정 진단처럼 표현하지 않습니다.
- 농약명이나 방제 방법을 직접 추천하는 경우 `safetyNotice`에 전문가 확인과 안전사용기준 확인을 포함합니다.
- 답변 실패 시에도 프론트가 표시할 수 있도록 구조화된 에러 또는 fallback 응답을 반환합니다.

## LangGraph MVP

1. 입력 검증
2. 이미지 이상 신호 추출
3. 사용자 식물/재배일지 맥락 요약
4. RAG 검색 query 생성
5. 공식 문서 검색
6. 답변 생성
7. 안전성 검토
8. 상담 이력 저장

## 배포

- MVP는 Render 또는 Railway를 추천합니다.
- Docker 기반 배포가 필요하면 `server/`의 설정을 사용합니다.
- `/health` endpoint는 배포 health check로 사용합니다.
