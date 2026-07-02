# Data Catalog

출처, 카테고리, chunk schema, 수집 이력을 관리하는 폴더입니다.

## 파일

- `source_registry.json`: 파이프라인이 실제로 읽는 구조화된 출처 registry. 여기의 `source_id` 값은 사람이 읽는 출처 key로 쓰고, DB 적재용 UUID `source_id`는 스크립트가 자동 생성합니다.
- `sources.csv`: 사람이 확인하기 쉬운 출처 목록. `source_key` 기준으로 관리합니다.
- `category_taxonomy.json`: RAG category, symptom keyword, safety tag 정의
- `chunk-schema.md`: Backend/Supabase 적재용 RAG chunk schema
- `collection-log.md`: 수집/전처리 작업 이력

## 운영 규칙

- 새 출처를 추가할 때는 `source_registry.json`과 `sources.csv`를 함께 갱신합니다.
- API key가 필요한 출처는 `api_key_env`에 환경변수명을 적고 실제 key는 `.env`에만 둡니다.
- 출처별 이용조건이 확실하지 않으면 `license`를 `verify_required` 또는 확인 필요 문구로 남깁니다.
- 병해충/농약 관련 출처는 반드시 `safety_tags`에 `expert_check_required` 또는 `pesticide_caution`을 포함합니다.
