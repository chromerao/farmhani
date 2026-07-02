# Data Scripts

## AI Hub In-door 육묘장 생장 데이터

AI Hub `71829` In-door 육묘장 생장 데이터는 1차 보조 데이터입니다. 원본 이미지와 `Other.zip`은 용량이 크므로 MVP에서는 받지 않고, 라벨 ZIP만 받아 작물별 생장단계 RAG 요약 문서와 이미지 manifest를 생성합니다.

우선순위 1 라벨 ZIP은 상추 3단계와 토마토 4단계입니다.

```bash
python data/scripts/download_aihub_seedling_growth.py --dry-run
python data/scripts/download_aihub_seedling_growth.py
python data/scripts/collect_aihub_seedling_growth.py
```

특정 file key만 받을 때:

```bash
python data/scripts/download_aihub_seedling_growth.py --file-key 553028
```

고추, 파프리카, 배추, 양배추까지 확장하려면 priority 2까지 받습니다.

```bash
python data/scripts/download_aihub_seedling_growth.py --max-priority 2
```

생성 산출물:

```text
data/interim/aihub_seedling_growth_labels.jsonl
data/interim/aihub_seedling_growth_documents.jsonl
data/interim/aihub_seedling_growth_image_manifest.csv
```

## AI Hub 원예식물 우선 수집

AI Hub `065.원예식물_화분류_물주기_수분공급 주기_생육데이터`는 원천 이미지가 매우 크므로 1차 MVP에서는 라벨 ZIP만 우선 수집합니다. 라벨 JSON에서 식물명, 수분 환경, 토양 상태, 센서값, 관수 상태를 추출해 RAG 요약 문서와 이미지 manifest를 만듭니다.

필요 환경변수:

```bash
AIHUB_API_KEY=...
```

AI Hub 공식 shell script 호환이 필요하면 `AIHUB_APIKEY`도 사용할 수 있습니다. 이 repo의 Python 스크립트는 두 이름을 모두 인식합니다.

우선순위 1 라벨 ZIP 다운로드 대상 확인:

```bash
python data/scripts/download_aihub_horticulture.py --dry-run
```

우선순위 1 라벨 ZIP 다운로드:

```bash
python data/scripts/download_aihub_horticulture.py
```

특정 file key만 받을 때:

```bash
python data/scripts/download_aihub_horticulture.py --file-key 521747
```

기본 저장 위치:

```text
data/external/aihub/horticulture/
```

라벨 ZIP 파싱 및 RAG 문서/이미지 manifest 생성:

```bash
python data/scripts/collect_aihub_horticulture.py
```

생성 산출물:

```text
data/interim/aihub_horticulture_labels.jsonl
data/interim/aihub_horticulture_documents.jsonl
data/interim/aihub_horticulture_image_manifest.csv
```

이후 기존 RAG 파이프라인을 그대로 실행합니다.

```bash
python data/scripts/normalize_documents.py
python data/scripts/chunk_documents.py
python data/scripts/embed_chunks.py --mode hash
python data/scripts/validate_processed_data.py
```

OpenAI 임베딩과 Supabase 적재는 각각 `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`가 준비된 뒤 실행합니다.

이 폴더는 데이터팀이 반복 실행할 수 있는 수집/전처리/RAG 적재 스크립트를 둡니다.

## 빠른 실행

```bash
python data/scripts/run_pipeline.py --collect-web
```

이 명령은 공개 웹 출처를 수집하고, 문서 정규화, chunk 생성, 검증까지 실행합니다.

식물/작물 검색 커버리지를 먼저 넓히려면 기본 seed catalog를 생성합니다.

```bash
python data/scripts/run_pipeline.py --build-plant-catalog
```

Supabase `plant_catalog`까지 적재하려면 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`를 준비한 뒤 실행합니다.

```bash
python data/scripts/run_pipeline.py --build-plant-catalog --load-plant-catalog
```

농사로 실내식물/작목정보 상세 문서를 넓게 수집하려면 다음 옵션을 사용합니다. 이 명령은 API key 없이 공개 웹 상세 페이지를 따라가며, 결과는 `data/interim/web_documents.core_plants.jsonl`에 저장됩니다.

```bash
python data/scripts/run_pipeline.py --collect-core-plants
```

## 단계별 명령

### 1. 공개 웹 출처 수집

```bash
python data/scripts/collect_web_sources.py
```

기본값은 우선순위 1~3 출처만 수집합니다. AI Hub/날씨 같은 2차 확장 출처까지 모두 수집하려면:

```bash
python data/scripts/collect_web_sources.py --all
```

특정 출처만 수집:

```bash
python data/scripts/collect_web_sources.py --source-id nongsaro_indoor_catalog
```

농사로 출처는 목록 페이지만 저장하지 않고 상세 링크도 함께 따라갑니다. 기본값은 출처별 최대 12개 상세 페이지입니다.

```bash
python data/scripts/collect_web_sources.py --source-id nongsaro_indoor_catalog --max-detail-pages 20
python data/scripts/collect_web_sources.py --source-id nongsaro_crop_tech --max-detail-pages 20
```

실내식물 전체와 주요 작물 커버리지를 늘릴 때:

```bash
python data/scripts/collect_web_sources.py --source-id nongsaro_indoor_catalog --source-id nongsaro_crop_tech --max-detail-pages 250 --output data/interim/web_documents.core_plants.jsonl
```

상세 수집 없이 목록 페이지만 저장하려면:

```bash
python data/scripts/collect_web_sources.py --source-id nongsaro_indoor_catalog --no-details
```

현재 상세 링크 추출 기준:

- `nongsaro_indoor_catalog`: `fncContentSub(cntntsNo)`로 노출되는 실내식물 상세 페이지
- `nongsaro_crop_tech`: `curationDtl.ps`, `contentNsSub.ps`, `farmTechMain.ps?stdPrdlstCode=...`처럼 HTML에 직접 노출되는 작목/재배 상세 페이지

농사로 작목정보는 선택된 작목이나 세션 상태에 따라 상세 링크 노출량이 달라질 수 있습니다. 상세 링크가 없는 경우 목록/메인 문서만 저장됩니다.

### 2. NCPMS 수집

OpenAPI endpoint가 확정되기 전에는 guide만 수집합니다.

```bash
python data/scripts/collect_ncpms.py
```

데이터팀이 수동 조사한 JSONL을 정규화:

```bash
python data/scripts/collect_ncpms.py --manual-jsonl data/interim/ncpms_manual_review.jsonl --crop 토마토
```

NCPMS 병 검색(`SVC01`)은 작물명 또는 병 한글명으로 `sickKey`를 찾는 API입니다. 1차 MVP에서는 검색 결과만 저장하기보다 `--fetch-details`를 붙여 `SVC05` 병 상세정보까지 바로 수집합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC01 --crop 토마토 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC01 --sick-name-kor 잎곰팡이병 --fetch-details
```

필요하면 검색 결과 목록만 저장할 수도 있습니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC01 --crop 토마토
```

NCPMS 해충 검색(`SVC03`)은 작물명 또는 해충 한글 종명으로 `insectKey`를 찾는 API입니다. `--fetch-details`를 붙이면 `SVC07` 해충 상세정보까지 바로 수집합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC03 --crop 토마토 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC03 --insect-kor-name 진딧물 --fetch-details
```

해충 상세정보(`SVC07`)를 직접 호출하려면 `insectKey`가 필요합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC07 --insect-key 98765
python data/scripts/collect_ncpms.py --service-code SVC07 --insect-keys-file data/interim/ncpms_insect_keys.txt
```

NCPMS 병해충 상담 검색(`SVC41`)은 유사 상담 사례를 찾는 API입니다. 1차 MVP에서는 전문 진단 근거가 아니라 유사 증상 사례 참고로만 사용합니다. `--fetch-details`를 붙이면 `SVC42` 상담 상세정보까지 바로 수집합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC41 --crop 토마토 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC41 --dgnss-req-sj 잎이 노랗게 변함 --fetch-details
```

상담 상세정보(`SVC42`)를 직접 호출하려면 `dgnssReqNo`가 필요합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC42 --dgnss-req-no 123456
python data/scripts/collect_ncpms.py --service-code SVC42 --dgnss-req-nos-file data/interim/ncpms_consult_req_nos.txt
```

NCPMS 통합검색(`SVC16`)은 병/해충/잡초 항목을 넓게 찾는 discovery API입니다. `detailUrl`의 상세키 형식이 서비스별로 다를 수 있으므로 1차 파이프라인에서는 상세 자동 호출에 쓰지 않고 검색 결과와 대표 이미지/상세키 정보를 저장합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC16 --search-name 토마토
python data/scripts/collect_ncpms.py --service-code SVC16 --crop 토마토 --kor-name 진딧물
python data/scripts/collect_ncpms.py --service-code SVC16 --div-code 병해충잡초구분코드 --param displayCount=50
```

NCPMS 병 상세정보(`SVC05`)를 직접 호출하려면 `sickKey`가 필요합니다. `NCPMS_API_KEY`를 루트 `.env`에 넣은 뒤 다음처럼 실행합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC05 --sick-key 12345
```

여러 병 상세정보를 한 번에 수집할 때는 `--sick-key`를 반복하거나 파일을 사용합니다.

```bash
python data/scripts/collect_ncpms.py --service-code SVC05 --sick-key 12345 --sick-key 67890
python data/scripts/collect_ncpms.py --service-code SVC05 --sick-keys-file data/interim/ncpms_sick_keys.txt
```

`data/interim/ncpms_sick_keys.txt`는 한 줄에 하나씩 `sickKey`를 적습니다. JSONL을 쓰는 경우 각 줄에 `{"sickKey": 12345}` 형태도 허용됩니다.

작물 대분류 이미지 검색(`SVC11`)처럼 `serviceType`이 필요한 API는 범용 endpoint 호출로 수집합니다. 이 데이터는 RAG 본문보다는 이미지/카테고리 manifest 보조 데이터로 분류합니다.

```bash
python data/scripts/collect_ncpms.py --endpoint-url http://ncpms.rda.go.kr/npmsAPI/service --param serviceCode=SVC11 --param serviceType=AA003 --param displayCount=50 --param startPoint=1
```

수동 JSONL 권장 필드:

```json
{
  "crop": "토마토",
  "disease_name": "잎곰팡이병",
  "symptom": "잎에 반점이 생김",
  "occurrence_condition": "고온다습 조건에서 발생 가능",
  "observation_point": "잎 뒷면, 줄기 주변 확인",
  "control_note": "전문가 확인 및 안전사용기준 확인 필요",
  "source_url": "https://ncpms.rda.go.kr/npms/OpenApiInfo.np"
}
```

### 3. PSIS API 수집

`.env`에 `PSIS_API_KEY`가 있어야 합니다.

```bash
python data/scripts/collect_psis.py --crop 토마토 --pest 잎곰팡이병
```

PSIS 데이터는 `safety_reference_only`로만 저장합니다. Backend 답변에서 농약 처방처럼 노출하면 안 됩니다.

### 4. AI Hub 이미지 manifest 생성

이미지 파일은 Git에 넣지 않고 manifest만 만듭니다.

```bash
python data/scripts/build_image_manifest.py --input data/interim/aihub_image_review.jsonl
```

입력 JSONL 예시:

```json
{
  "image_id": "aihub_sample_001",
  "storage_path": "supabase://plant-reference/aihub/sample_001.jpg",
  "plant_name": "토마토",
  "label": "leaf_yellowing",
  "status": "abnormal",
  "notes": "원본 파일은 Git 외부 저장"
}
```

### 5. 식물 master 생성

프론트 식물 등록/검색 자동완성이나 향후 `GET /api/v1/plant-catalog` 후보 데이터가 필요할 때 사용합니다.

```bash
python data/scripts/build_plant_master.py --input data/interim/plant_records.reviewed.jsonl
```

입력 JSONL 필수 필드:

```json
{
  "name_ko": "몬스테라",
  "name_scientific": "Monstera deliciosa",
  "category": ["indoor", "foliage"],
  "light_requirement": "밝은 간접광",
  "water_requirement": "흙 표면이 마르면 충분히 관수",
  "source_id": "nongsaro_indoor_catalog",
  "source_url": "https://www.nongsaro.go.kr/...",
  "license": "verify_required"
}
```

### 6. 문서 정규화

```bash
python data/scripts/normalize_documents.py
```

### 7. 청킹

```bash
python data/scripts/chunk_documents.py
```

### 8. 임베딩

운영/실제 RAG:

```bash
python data/scripts/embed_chunks.py --mode openai
```

로컬 smoke test:

```bash
python data/scripts/embed_chunks.py --mode hash
```

### 9. Supabase pgvector 적재

`.env`에 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`가 필요합니다.

```bash
python data/scripts/load_supabase_pgvector.py --replace
```

적재 전 dry run:

```bash
python data/scripts/load_supabase_pgvector.py --dry-run
```

### 10. 검증

```bash
python data/scripts/validate_processed_data.py
```

식물명 카탈로그 대비 RAG 관리 문서 커버리지 확인:

```bash
python data/scripts/validate_data_coverage.py
```

`Only weak/reference matches`는 병해충/AI Hub 라벨 요약처럼 관리 가이드로 보기 약한 문서만 있는 식물입니다. `No RAG matches`는 식물명 카탈로그에는 있지만 RAG 문서가 없는 항목입니다.

아직 산출물이 없을 때 script 자체만 확인:

```bash
python data/scripts/validate_processed_data.py --allow-missing
```

## 산출물

| 파일 | 설명 | Git 커밋 |
|---|---|---|
| `data/raw/<source_id>/*` | 원본 HTML/API 응답 | 금지 |
| `data/interim/*.jsonl` | 중간 수집/정규화 결과 | 금지 |
| `data/processed/rag_sources.sample.jsonl` | Supabase `rag_sources` 후보 | 기본 금지 |
| `data/processed/rag_chunks.sample.jsonl` | RAG chunk 후보 | 기본 금지 |
| `data/vectorstore/rag_chunks.embedded.jsonl` | embedding 포함 결과 | 금지 |

## Backend 테이블 매핑

```text
rag_sources.source_id   <- source_id
rag_sources.title       <- title
rag_sources.url         <- url
rag_sources.publisher   <- publisher

rag_chunks.source_id    <- source_id
rag_chunks.text         <- text
rag_chunks.embedding    <- embedding
rag_chunks.symptom_keywords <- symptom_keywords
```

`source_id`와 `chunk_id`는 UUID 문자열입니다. 원래 출처 식별자는 `source_key`, `chunk_key`로 함께 보관합니다.
