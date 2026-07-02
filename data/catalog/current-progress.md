# 현재 데이터 수집 진행 상황

최종 업데이트: 2026-07-01  
담당: data-team

## 커밋 정책

- `data/raw/`, `data/external/`, `data/interim/`, `data/processed/`, `data/vectorstore/`의 원본/중간/대용량 산출물은 Git에 커밋하지 않는다.
- API 키, 서비스 시크릿, Supabase service role key, 개인 토큰은 어떤 문서나 노트북에도 기록하지 않는다.
- 수집 상태는 catalog 문서와 재현 가능한 script로 남긴다.
- 팀원이 만든 로컬 산출물은 문서에 경로와 요약만 기록하고, 필요 시 소규모 정제 샘플을 별도로 만든다.

## 현재 반영된 파이프라인

- 농사로 웹 상세 수집: `data/scripts/collect_web_sources.py`
- NCPMS 병/해충/상담 검색 및 상세 수집: `data/scripts/collect_ncpms.py`
- PSIS 안전 참고 수집: `data/scripts/collect_psis.py`
- AI Hub 원예식물 물주기 라벨 다운로드/파싱: `data/scripts/download_aihub_horticulture.py`, `data/scripts/collect_aihub_horticulture.py`
- AI Hub In-door 육묘장 생장 라벨 다운로드/파싱: `data/scripts/download_aihub_seedling_growth.py`, `data/scripts/collect_aihub_seedling_growth.py`
- RAG 정규화/청킹/임베딩/Supabase 적재: `normalize_documents.py`, `chunk_documents.py`, `embed_chunks.py`, `load_supabase_pgvector.py`

## AI Hub 수집 현황

### 원예식물 물주기 생육데이터

- 데이터셋: `71705`
- 수집 완료: 스투키, 선인장, 금전수, 호접란, 스파티필럼, 몬스테라 라벨 ZIP
- 파싱 결과: 라벨 152,645건, RAG 요약 문서 18건, 이미지 manifest 152,645행
- 원본 ZIP과 생성 산출물은 Git ignore 대상이다.

### In-door 육묘장 생장 데이터

- 데이터셋: `71829`
- priority 1: 상추 3단계, 토마토 4단계 라벨 ZIP
- priority 2: 고추, 파프리카, 배추, 양배추 라벨 ZIP
- 원본 이미지와 `Other.zip`은 MVP 수집 대상에서 제외한다.

## feature/data1 검토 결과

`feature/data1` 브랜치의 유효한 데이터 자료는 아래처럼 선별 반영했다.

- 반영: `data/catalog/current-progress.md`
- 반영: `data/catalog/nongsaro_5_crops_collection_instr.md`
- 반영: `data/catalog/nongsaro_garden_instr.md`
- 내용 흡수: 농사로 cropEbook, 실내정원 code mapping, 주간농사정보 manifest 존재 여부

반영하지 않은 항목:

- 백엔드/프론트/루트 파일 삭제 및 변경
- `pyproject.toml`, `uv.lock`, `.python-version` 삭제
- 노트북 2개
- HWP 및 API 샘플 소스 묶음
- 로컬 절대경로가 포함된 weekly farming manifest 원본

## feature/data1 로컬 산출물 요약

팀원 문서 기준으로 아래 산출물이 로컬에 생성되었다.

- 농사로 작목기술정보: 토마토, 고추, 상추, 오이, 딸기 대상
- 농사로 실내정원: `gardenList`, `gardenDtl` 기반 20개 실내식물 정규화 레코드
- NCPMS 병해: 검색 결과 98행, 상세/병합 결과 390행
- NCPMS 해충: 검색 결과 55행, 상세/병합 결과 238행
- 이미지 manifest: 37행

이 산출물들은 브랜치에 tracked file로 포함되어 있지 않으므로, 필요한 경우 팀원에게 재현 스크립트 또는 정제 샘플 형태로 다시 공유 요청한다.

## 다음 단계

- 농사로 cropEbook API 수집기는 현재 문서화만 반영되어 있으므로, 필요 시 `collect_nongsaro_crop_ebook.py`로 별도 구현한다.
- 주간농사정보는 로컬 절대경로가 포함된 manifest를 그대로 쓰지 않고, 수집기로 재생성한다.
- RAG 인입 전 모든 문서는 `source_id`, `title`, `publisher`, `url`, `collected_at`, `license`, `category`, `crop_or_plant`, `symptom_keywords`, `safety_tags`를 포함해야 한다.
