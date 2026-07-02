# Collection Log

데이터 수집/전처리 작업 이력을 날짜순으로 기록합니다.

## 2026-07-01

- `feature/data1` 브랜치를 검토했습니다. 백엔드/프론트/루트 삭제 변경이 섞여 있어 병합하지 않고, 데이터 문서만 선별 반영했습니다.
- `feature/data1`에서 `current-progress.md`, `nongsaro_5_crops_collection_instr.md`, `nongsaro_garden_instr.md`를 반영했습니다.
- `feature/data1`의 weekly farming manifest는 로컬 절대경로가 포함되어 있어 원본 CSV는 반영하지 않고, `weekly_farming_info` 출처만 catalog에 등록했습니다.
- 농사로 `cropEbook` API 출처를 `sources.csv`와 `source_registry.json`에 추가했습니다.
- AI Hub `71829` In-door 육묘장 생장 데이터를 1차 보조 데이터로 파이프라인에 등록했습니다. `data/catalog/aihub_seedling_growth_files.json`, `data/scripts/download_aihub_seedling_growth.py`, `data/scripts/collect_aihub_seedling_growth.py`를 추가했습니다.
- 기본 수집 우선순위는 상추/토마토 라벨 ZIP이며, 고추/파프리카/배추/양배추는 priority 2 확장 대상으로 분류했습니다. 원본 이미지와 `Other.zip`은 MVP 수집 대상에서 제외했습니다.
- AI Hub `71705` 원예식물 물주기 데이터의 공식 다운로드 API 방식을 확인하고, `data/scripts/download_aihub_horticulture.py`를 추가했습니다.
- 최우선 라벨 ZIP 6종(스투키, 선인장, 금전수, 호접란, 스파티필럼, 몬스테라)을 `data/external/aihub/horticulture/`에 수집했습니다. 원본 ZIP은 Git ignore 대상입니다.
- `data/scripts/collect_aihub_horticulture.py`로 라벨 JSON 152,645건을 파싱해 RAG 요약 문서 18건과 이미지 manifest 152,645행을 생성했습니다. 생성 산출물은 `data/interim/`, `data/processed/`의 Git ignore 대상입니다.
- `data_sourcing` 브랜치의 카탈로그 변경을 검토했고, PSIS, AI Hub 이미지, 공공데이터포털 농업기상 수집 상태를 현재 catalog 구조에 흡수했습니다.

## 2026-06-30

- `source_registry.json`과 `category_taxonomy.json`을 추가해 출처, API key 필요 여부, category, safety tag를 구조화했습니다.
- 문서 저장, 정규화, 청킹, 임베딩, Supabase pgvector 적재 파이프라인 스크립트를 추가했습니다.
- `sources.csv`를 사람이 읽기 쉬운 UTF-8 CSV로 정리했습니다.
- 농사로 상세 수집, NCPMS 병/해충/상담 검색 및 상세 수집, PSIS 수집, Supabase 적재 스크립트의 기본 구조를 추가했습니다.
- smoke test는 임시 샘플 문서 1건으로 정규화, 청킹, hash 임베딩, 검증까지 완료했습니다.

## 2026-06-29

- 프로젝트 초기 source catalog와 chunk schema 초안을 생성했습니다.
- 실제 원문 수집은 진행하지 않았습니다.
