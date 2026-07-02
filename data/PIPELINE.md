# Farmhani Data Pipeline

## AI Hub In-door 육묘장 생장 데이터

AI Hub `71829` In-door 육묘장 생장 데이터는 상추, 토마토, 고추, 파프리카, 배추, 양배추의 육묘 생장단계 보조 데이터로 사용한다. 원본 이미지와 `Other.zip`은 MVP에서 제외하고 라벨 ZIP만 우선 수집한다.

```bash
python data/scripts/download_aihub_seedling_growth.py --dry-run
python data/scripts/download_aihub_seedling_growth.py
python data/scripts/collect_aihub_seedling_growth.py
```

`collect_aihub_seedling_growth.py`는 라벨 ZIP 내부 JSON을 읽어 `data/interim/aihub_seedling_growth_documents.jsonl`을 만들며, 이 파일은 기존 `normalize_documents.py`의 기본 입력에 자동 포함된다. 기본 우선순위 1은 상추와 토마토 라벨이며, 고추/파프리카/배추/양배추는 `--max-priority 2`로 확장한다.

## AI Hub 원예식물 라벨 우선 수집

1차 MVP의 실내 식물 관리 답변 보강을 위해 AI Hub `71705` 데이터셋은 원천 이미지 전체가 아니라 라벨 ZIP을 먼저 수집한다. 우선순위 파일 목록은 `data/catalog/aihub_horticulture_files.json`에서 관리한다.

```bash
python data/scripts/download_aihub_horticulture.py --dry-run
python data/scripts/download_aihub_horticulture.py
python data/scripts/collect_aihub_horticulture.py
```

`collect_aihub_horticulture.py`는 라벨 ZIP 내부 JSON을 읽어 `data/interim/aihub_horticulture_documents.jsonl`을 만들며, 이 파일은 기존 `normalize_documents.py`의 기본 입력에 자동 포함된다. 원천 이미지 ZIP은 용량이 크므로 이미지 모델 학습 또는 시각 검증이 필요할 때만 `--kind source_image --max-priority 3`로 별도 수집한다.

이 문서는 `Farm하니? / 식물 주치의 AI` 프로젝트의 데이터 수집, 전처리, 청킹, 임베딩, Supabase pgvector 적재 기준입니다.

목표는 많은 데이터를 한 번에 모으는 것이 아니라, **출처와 안전 기준이 추적되는 RAG 문서 파이프라인**을 만드는 것입니다. Backend는 이 파이프라인이 만든 `rag_sources`, `rag_chunks` 데이터를 Supabase에서 검색합니다.

## 1. 카테고리 분류 기준

| category | 우선순위 | 용도 | 출처 |
|---|---:|---|---|
| `indoor_care` | 1 | 실내식물 물주기, 광도, 온도, 과습/건조 관리 | 농사로 실내식물 정보 |
| `crop_care` | 1 | 토마토/고추/상추/오이/딸기 재배관리 | 농사로 작목정보 |
| `plant_catalog` | 1 | 식물명/작물명 검색, 자동완성, 별칭 | Farmhani seed, 향후 국가식물목록 |
| `ornamental_care` | 1 | 장미/벚꽃/개나리/해바라기 등 관상식물 | seed catalog, 향후 식물도감 |
| `herb` | 1 | 바질/로즈마리/민트 등 가정재배 허브 | seed catalog, 향후 농사로/식물도감 |
| `pest_reference` | 2 | 병해충 증상 참고, 관찰 포인트 | NCPMS |
| `pesticide_safety` | 3 | 농약 안전사용기준 확인용 참고 | PSIS |
| `image_reference` | 4 | 이미지 manifest, 향후 비전 모델/증상 taxonomy | AI Hub |
| `weather_context` | 5 | 향후 기상 기반 위험도 보정 | 농업날씨365 |

상세 분류와 symptom keyword는 [category_taxonomy.json](catalog/category_taxonomy.json)에 둡니다.

## 2. 출처별 수집 전략

| source_id | 수집 방식 | API key | 1차 MVP 처리 |
|---|---|---|---|
| `nongsaro_indoor_catalog` | public web fetch | 불필요 | HTML 저장 후 본문 추출, RAG/plant catalog 후보 |
| `nongsaro_crop_tech` | public web fetch | 불필요 | 작목별 관리 문서 추출 |
| `farmhani_priority_plant_seed` | local reviewed JSONL | 불필요 | 식물 등록/자동완성 기본 카탈로그 |
| `ncpms_openapi_guide` | public web fetch | 조사용 | OpenAPI 안내와 승인 절차 문서화 |
| `ncpms_pest_reference` | API 또는 manual JSONL | `NCPMS_API_KEY` | 승인 전에는 수동 조사 JSONL을 같은 schema로 정규화 |
| `psis_pesticide_safety` | OpenAPI | `PSIS_API_KEY` | 안전사용기준 참고용으로만 저장 |
| `aihub_agriculture_datasets` | catalog/manual manifest | `AIHUB_API_KEY` 가능 | 이미지 원본은 Git 금지, manifest만 생성 |
| `rda_weather365` | web/API later | `WEATHER_API_KEY` 가능 | 2차 확장 후보 |

상세 출처 registry는 [source_registry.json](catalog/source_registry.json)에 있습니다.

## 3. 폴더별 역할

```text
data/
  catalog/       # source registry, taxonomy, schema 문서
  raw/           # 원본 HTML/API 응답 저장. Git 커밋 금지
  interim/       # 중간 정규화 결과. Git 커밋 금지
  processed/     # 최종 JSONL/CSV 산출물. 기본 Git 커밋 금지
  vectorstore/   # embedding 포함 파일. Git 커밋 금지
  scripts/       # 재현 가능한 수집/전처리/적재 스크립트
```

## 4. 파이프라인 단계

### 4.1 문서 저장

공개 웹 출처를 수집합니다.

```bash
python data/scripts/collect_web_sources.py
```

기본값은 우선순위 1~3 출처만 수집합니다. AI Hub/날씨 같은 확장 후보까지 수집하려면 `--all`을 명시합니다.

농사로 출처는 상세 수집이 기본으로 켜져 있습니다. 실내식물은 `fncContentSub(cntntsNo)` 상세 페이지를 따라가고, 작목정보는 HTML에 노출된 `curationDtl.ps`, `contentNsSub.ps`, `farmTechMain.ps?stdPrdlstCode=...` 링크를 따라갑니다.

```bash
python data/scripts/collect_web_sources.py --source-id nongsaro_indoor_catalog --max-detail-pages 20
python data/scripts/collect_web_sources.py --source-id nongsaro_crop_tech --max-detail-pages 20
python data/scripts/collect_web_sources.py --source-id nongsaro_indoor_catalog --no-details
```

작목정보는 농사로 화면에서 선택된 작목 또는 HTML 노출 상태에 따라 상세 링크 수가 달라질 수 있습니다. 상세 링크가 없는 경우 목록/메인 문서만 저장하고, 이후 작목별 URL이나 검색 API가 확보되면 seed URL을 추가합니다.

결과:

- 원본 HTML: `data/raw/<source_id>/*.html`
- 본문 후보 JSONL: `data/interim/web_documents.jsonl`

PSIS는 API key가 있을 때만 호출합니다.

```bash
python data/scripts/collect_psis.py --crop 토마토 --pest 잎곰팡이병
```

NCPMS는 승인 전에는 guide만 저장하거나, 데이터팀이 수동 조사한 JSONL을 넣습니다. 승인 후에는 `SVC01` 병 검색 API로 `sickKey`를 찾고, 이어서 `SVC05` 병 상세정보 API를 수집합니다. 1차 MVP에서는 전문 진단/처방이 아니라 증상 관찰과 관리 가이드 보조 근거로만 사용합니다.

```bash
python data/scripts/collect_ncpms.py
python data/scripts/collect_ncpms.py --manual-jsonl data/interim/ncpms_manual_review.jsonl --crop 토마토
python data/scripts/collect_ncpms.py --service-code SVC01 --crop 토마토 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC01 --sick-name-kor 잎곰팡이병 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC03 --crop 토마토 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC03 --insect-kor-name 진딧물 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC07 --insect-key 98765
python data/scripts/collect_ncpms.py --service-code SVC41 --crop 토마토 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC41 --dgnss-req-sj 잎이 노랗게 변함 --fetch-details
python data/scripts/collect_ncpms.py --service-code SVC42 --dgnss-req-no 123456
python data/scripts/collect_ncpms.py --service-code SVC16 --search-name 토마토
python data/scripts/collect_ncpms.py --service-code SVC05 --sick-key 12345
python data/scripts/collect_ncpms.py --service-code SVC05 --sick-keys-file data/interim/ncpms_sick_keys.txt
```

`SVC01` 응답의 `sickKey`를 병 상세 조회키로 사용합니다. `SVC03` 응답의 `insectKey`를 해충 상세 조회키로 사용해 `SVC07`을 호출합니다.

`SVC05` 응답은 `cropName`, `sickNameKor`, `infectionRoute`, `developmentCondition`, `symptoms`, `preventionMethod`, `biologyPrvnbeMth`, `chemicalPrvnbeMth`, `virusName`, `sfeNm`, `imageList` 등을 RAG 문서 본문과 메타데이터로 정리합니다. `chemicalPrvnbeMth` 또는 농약/약제 관련 문구가 있으면 `pesticide_caution` tag를 붙여 Backend 답변에서 안전 문구를 강제할 수 있게 합니다.

`SVC07` 응답은 `cropName`, `insectSpeciesKor`, `insectSpecies`, `distrbInfo`, `stleInfo`, `ecologyInfo`, `damageInfo`, `preventMethod`, `biologyPrvnbeMth`, `chemicalPrvnbeMth`, `imageList`, `enemyInsectSpeciesKor` 등을 RAG 문서 본문과 메타데이터로 정리합니다. `SVC07` 응답의 `insectKey` 필드는 천적곤충 상세키로도 쓰일 수 있으므로, 실제 상세 조회에 사용한 해충 키는 `raw_record._detail_insectKey`에 별도로 보존합니다.

`SVC41` 응답의 `dgnssReqNo`를 상담 상세 조회키로 사용해 `SVC42`를 호출합니다. `SVC42` 응답은 `dgnssReqSj`, `cropName`, `reqestCn`, `dbyhs`, `dgnssOpin`, `prvnbeMth`, `imageList` 등을 유사 상담 사례 문서로 정리합니다. 이 데이터는 전문가 상담 이력 기반 참고 사례이므로 `usage_scope=expert_case_reference`, `safety_tags=expert_case_reference`로 저장하고, Backend 답변에서는 확정 진단이나 직접 처방처럼 사용하지 않습니다.

`SVC16` 통합검색은 병/해충/잡초 항목을 넓게 탐색하는 discovery API입니다. 응답의 `detailUrl`은 상세키정보로 저장하되, 1차 RAG 본문 생성은 `SVC01/SVC05`, `SVC03/SVC07`, `SVC41/SVC42`처럼 서비스별 검색/상세 API를 우선 사용합니다.

### 4.2 데이터 전처리

모든 interim 문서를 공통 RAG 문서 schema로 정규화합니다.

```bash
python data/scripts/normalize_documents.py
```

결과:

- `data/interim/rag_documents.normalized.jsonl`

필수 필드:

- `doc_id`
- `source_id`: Supabase DB에 들어가는 UUID 문자열
- `source_key`: 사람이 읽는 출처 key. 예: `nongsaro_indoor_catalog`
- `title`
- `publisher`
- `url`
- `license`
- `collected_at`
- `category`
- `crop_or_plant`
- `symptom_keywords`
- `safety_tags`
- `text`

### 4.3 청킹

정규화 문서를 500~800 token에 가까운 길이의 chunk로 나눕니다. 현재 구현은 외부 tokenizer 없이 2,200자 기준으로 자릅니다.

```bash
python data/scripts/chunk_documents.py
```

결과:

- `data/processed/rag_sources.sample.jsonl`
- `data/processed/rag_chunks.sample.jsonl`

`rag_chunks.sample.jsonl`은 Backend가 직접 읽는 `rag_chunks.text`, `rag_chunks.symptom_keywords` 컬럼에 맞춰 생성됩니다. `source_id`와 `chunk_id`는 UUID 문자열이며, 사람이 읽는 기존 출처 키는 `source_key`, `chunk_key`에 남깁니다.

### 4.3.1 식물 검색 카탈로그

RAG 답변용 문서와 별도로 식물 등록/검색/자동완성용 `plant_catalog`를 생성합니다. 기본 seed는 `data/catalog/priority_plant_catalog.jsonl`이며, 딸기/고구마/장미/벚꽃/개나리/해바라기처럼 일반 사용자가 자주 찾는 식물과 작물을 우선 포함합니다.

```bash
python data/scripts/build_plant_master.py
python data/scripts/load_plant_catalog.py --dry-run
```

Supabase 적재:

```bash
python data/scripts/load_plant_catalog.py
```

전체 파이프라인 옵션:

```bash
python data/scripts/run_pipeline.py --build-plant-catalog --load-plant-catalog
```

### 4.4 임베딩

실제 적재 전에는 OpenAI embedding을 사용합니다.

```bash
python data/scripts/embed_chunks.py --mode openai
```

로컬 smoke test만 할 때는 명시적으로 hash mode를 씁니다. 이 결과는 운영 RAG 품질 검증에 쓰지 않습니다.

```bash
python data/scripts/embed_chunks.py --mode hash
```

결과:

- `data/vectorstore/rag_chunks.embedded.jsonl`

### 4.5 Supabase pgvector 저장

Supabase service role key가 필요합니다. 이 key는 절대 frontend에 넣지 않습니다.

```bash
python data/scripts/load_supabase_pgvector.py --replace
```

매핑:

| 산출물 | Supabase table | 필드 |
|---|---|---|
| `rag_sources.sample.jsonl` | `rag_sources` | `source_id`, `title`, `url`, `publisher`, `collected_at` |
| `rag_chunks.embedded.jsonl` | `rag_chunks` | `chunk_id`, `source_id`, `text`, `embedding`, `symptom_keywords` |

### 4.6 재적재 전 품질 기준

기존 Supabase RAG 데이터를 삭제하고 다시 적재하기 전에는 현재 스크립트로 chunk를 재생성하고 검증을 통과시킵니다.

출처/공식 문서 패널 표시를 위해 다음 필드는 필수입니다.

- `rag_chunks.text`: Backend가 `content`로 받아 답변과 발췌문 생성에 쓰는 본문입니다.
- `rag_chunks.metadata.section`: citation에 표시할 문서 위치/섹션입니다.
- `rag_chunks.metadata.excerpt`: 공식 문서 패널에 표시할 짧은 발췌문입니다.
- `rag_chunks.metadata.contentPreview`: UI 호환용 발췌문입니다.
- `rag_chunks.symptom_keywords`: pgvector 실패 시 keyword fallback 검색에 쓰입니다.

현재 chunker는 너무 짧거나 숫자/표 중심인 조각을 제외합니다. 기상자료 표, ID 목록, 라벨만 있는 조각이 식물 관리 가이드처럼 임베딩되는 것을 막기 위한 기준입니다.

권장 사전 검증:

```bash
python data/scripts/normalize_documents.py
python data/scripts/chunk_documents.py
python data/scripts/validate_processed_data.py --allow-missing
```

## 5. 전체 실행 예시

공개 웹 문서 수집부터 chunk 검증까지:

```bash
python data/scripts/run_pipeline.py --collect-web
```

OpenAI embedding까지:

```bash
python data/scripts/run_pipeline.py --collect-web --embed --embed-mode openai
```

Supabase까지 적재:

```bash
python data/scripts/run_pipeline.py --collect-web --embed --embed-mode openai --load-supabase --replace
```

## 6. 검증

```bash
python data/scripts/validate_processed_data.py
```

검증 항목:

- source/chunk 필수 필드
- chunk id 중복
- chunk의 source id가 source 목록에 존재하는지
- 농약 관련 category의 `pesticide_caution` tag 포함 여부
- embedding vector 1536차원 여부

## 7. Backend 연동 기준

Backend는 Supabase에서 다음 흐름으로 검색합니다.

1. 사용자 질문과 최근 관리일지를 query text로 정리
2. 같은 `EMBEDDING_MODEL`로 query embedding 생성
3. `rag_chunks.embedding`과 cosine similarity 검색
4. `rag_sources` join 결과에서 citation 생성
5. 답변에는 `sourceId`, `title`, `url`, `publisher`를 포함

RAG 답변 안전 기준:

- 병명 확정 표현 금지
- 농약 직접 처방 금지
- `pesticide_caution`, `expert_check_required` tag가 있으면 안전 문구를 반드시 포함
- 검색 결과가 부족하면 추가 사진/관리 기록을 요청

## 8. 공식 출처

- 농사로 실내식물 정보: https://www.nongsaro.go.kr/portal/ps/psz/psza/contentMain.ps?menuId=PS00376&pageUnit=8
- 농사로 작목정보: https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291
- NCPMS OpenAPI 안내: https://ncpms.rda.go.kr/npms/OpenApiInfo.np
- PSIS OpenAPI 안내: https://psis.rda.go.kr/psis/cont/contentMain.ps?menuId=PS00381
- AI Hub 농축수산 데이터 목록: https://www.aihub.or.kr/aihubdata/data/list.do?currMenu=115&srchDataRealmCode=REALM004&topMenu=100
- 농업날씨365: https://weather.rda.go.kr/
