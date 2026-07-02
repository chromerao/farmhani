# Data Agent 지침

## 작업 범위

- 수정 가능: `data/`
- 읽기 권장: `docs/rag-langgraph.md`, `docs/architecture.md`
- 수정 전 합의 필요: `backend/`, `contracts/`, root 문서

## 책임

- 공식 문서/API 후보 조사
- 수집 source catalog 작성
- raw 자료 저장 위치와 라이선스 기록
- 전처리/정규화 script 작성
- RAG chunk 생성
- embedding 입력용 metadata schema 관리

## 금지 사항

- AI Hub 원본 이미지, 대용량 PDF, vector DB 파일을 Git에 커밋하지 않습니다.
- API key나 개인 인증 정보를 notebook에 저장하지 않습니다.
- 출처가 불명확하거나 사용 권한이 애매한 데이터를 RAG에 넣지 않습니다.

## 산출물 기준

- `data/catalog/`: source catalog, schema, 수집 로그
- `data/scripts/`: 재현 가능한 수집/전처리 script
- `data/processed/`: Git에는 예시 또는 작은 샘플만 허용
- `data/vectorstore/`: 실제 vector DB 파일 커밋 금지

## Metadata 필수 필드

- `source_id`
- `title`
- `publisher`
- `url`
- `collected_at`
- `license`
- `category`
- `crop_or_plant`
- `symptom_keywords`
- `chunk_id`
