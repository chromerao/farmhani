# RAG 고도화를 위한 이종 농업 데이터의 최종 전처리 결과 보고서 (Final Data Preprocessing Report)

본 보고서는 `Farm하니? / 식물 주치의 AI` 서비스의 RAG(Retrieval-Augmented Generation) 시스템 검색 무결성 및 응답 신뢰성 고도화를 위해 수행된 데이터 전처리 결과를 종합 정리한 최종 문서입니다. 

---

## 📌 1. 전처리 설계 요약 (두괄식)

*   **Step 1. 1차 정규화 및 데이터 클렌징**
    *   **[핵심 명제] 파편화된 이종 데이터를 통일된 RAG 표준 스키마(JSONL)로 매핑하고, Regex 필터링을 통해 텍스트 노이즈(HTML태그/공백)를 제거하여 벡터 왜곡을 방지합니다.**
*   **Step 2. 문맥 보존형 단락 분할 (청킹)**
    *   **[핵심 명제] 문맥 손실(Context Loss)과 정보 희석(Information Dilution)을 방지하기 위해 문장 경계를 보존하는 청크 사이즈(Chunk_size) 오버랩(Overlap)의 최적 단락 단위로 본문을 분할합니다.**
*   **Step 3. 고밀도 벡터 임베딩 및 안전 검증**
    *   **[핵심 명제] OpenAI `text-embedding-3-small` (1536차원) 모델을 통해 텍스트 의미 공간을 실수형 좌표로 변환하고, 로컬 선캐싱(Decoupling) 및 드라이런 검증을 거쳐 DB 업로드 정합성을 확보합니다.**

---

## 📂 2. 수집 및 전처리 대상 데이터셋 명세

RAG 데이터 파이프라인에 주입된 데이터 출처 및 개별 수집/정제 규칙 요약 테이블은 다음과 같습니다.
 - 현재 위치에선 청킹 단위/ 문서 단위가 혼재되어 있어 공통 청킹 단위 수량 구분은 문서 하단에서 확인할 수 있습니다. 이 부분은 참고 사항으로 확인하길 권장합니다

| 데이터 소스명 | 물리 파일명 | 레코드 수 | 카테고리 (Category) | 적재 상태 / 범위 | 수집 경로 및 전처리/정제 핵심 규칙 |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **식물 마스터** | `priority_plant_catalog.jsonl` (Seed) | 65종 | `plant_master` | **별도 테이블 적재** | `build_plant_master.py` 활용 / 학명, 영명, 이명(aliases), 과명 파싱 ➡️ `plant_catalog` 테이블 적재 |
| **PSIS 농약 정보** | `sample_4_psis_pesticide_60plants_raw.csv` | 100건 | `pesticide_safety` | **1차 실적재 완료** | 적용 약제 및 안전 희석 배수 추출 ➡️ 본문 내 방제 언급 시 `pesticide_caution` 태그 자동 주입 |
| **AI Hub 이미지 메타** | `sample_5_image_manifest_60plants_raw.csv` | 100건 | `weather_context` | **1차 실적재 완료** | 센서 라벨(수분, 관수 상태) 및 육묘 단계 JSON 텍스트 추출 ➡️ RAG 보조 데이터로 정제 |
| **기상 스트레스 가이드** | `sample_6_weather_disease_risk_60plants_raw.csv` | 100건 | `weather_context` | **1차 실적재 완료** | 기온/광도 임계점 매핑 ➡️ 식물 기후 위해 분석 가이드 및 행동 요령 텍스트화 |
| **국립수목원 식물도감** | `sample_national_botanic_garden_raw.csv` | 100건 | `indoor_care` | **1차 실적재 완료** | OpenAPI 연동 ➡️ 잎/꽃 형태 정보 등 특징 텍스트 추출, 표준 학명/과명 분류 매핑 |
| **농사로 작물/실내식물 정보** | `crop_farmtech_sections.json` | 14건 | `crop_care` | **1차 실적재 완료** | 농사로 `farmTechMain` 기반 작물 후보 수집 ➡️ 작물 코드, 상세 URL, 재배/병해충 관련 섹션 정보 구조화 |
| **농사로 작업일정 정보** | `nongsaro_work_documents.reparsed_from_hwpx.jsonl` | 132건 | `nongsaro_work_schedule` | **1차 실적재 완료** | HWPX XML 문단/표 재파싱 ➡️ 정형 표는 문장형 텍스트로 변환, 비정형 표는 행 구조를 보존하여 RAG용 `text`로 재구성 |
| **네이버 지식백과 보조 문서** | `naver_ency_preprocessed.jsonl` | 문서 33건 | `naver_encyclopedia` | **1차 실적재 완료** | API 호출 URL + 수동 검수 기반 본문 수집 ➡️ 제목, 본문, 출처, 작물명을 포함한 보조 지식 문서로 정규화 |
| **NCPMS 병해충 참고 정보** | `ncpms_pest_reference.jsonl` | 문서 382건 | `pest_reference` | **1차 실적재 완료** | 병 데이터와 해충 데이터를 단일 JSONL로 통합 ➡️ 작물명, 병해충명, 발생 조건, 증상/피해, 예방 정보를 `text`에 포함하고, `crop_or_plant`는 원본 작물 기준으로 유지하여 정규화  |

---

## 📐 3. 데이터 구조 및 전처리 파이프라인 설계

### 3.1 디렉토리 아키텍처 (`data/` 구조)
```text
data/
  ├─ catalog/       # 출처 registry(source_registry.json), 스키마 및 가이드 문서
  ├─ raw/           # Raw CSV, HTML, API raw 응답 등 원천 자료
  ├─ interim/       # 1차 전처리 완료된 중간 산출물 (.normalized.jsonl)
  ├─ processed/     # 2차 청킹 완료된 구조화 데이터 (.sample.jsonl)
  ├─ vectorstore/   # 3차 임베딩(1536차원 벡터) 완료 최종 적재용 데이터 (.embedded.jsonl)
  ├─ external/      # 대용량 자료 보관용 원외 저장함 (Git 커밋 배제)
  ├─ notebooks/     # 실험, 수동 검수 및 보조 전처리용 노트북(IPYNB) 공간
  └─ scripts/       # 재현 가능한 수집/정규화/청킹/임베딩/적재 파이썬 스크립트 일체
```


### 3.2 핵심 데이터 표준 스키마 규격

#### RAG 문서 정규화 스키마 (`data/interim/rag_documents.normalized.jsonl`)
```json
{
  "doc_id": "UUID (고유 문서 식별자)",
  "source_id": "UUID (출처 식별용 외래키)",
  "source_key": "사람 식별용 출처 key (예: national_botanic_garden)",
  "title": "문서 제목",
  "text": "Regex 클렌징(공백, HTML 태그 정화) 및 필드 병합이 완료된 순수 텍스트 본문",
  "category": "indoor_care | crop_care | pesticide_safety 등",
  "crop_or_plant": ["몬스테라"],
  "symptom_keywords": ["잎 노람", "과습"],
  "safety_tags": ["not_diagnosis", "expert_check_required", "pesticide_caution"],
  "collected_at": "YYYY-MM-DD",
  "source_url": "제공처 원본 URL",
  "license": "라이선스 정보"
}
```

---

## 🛠️ 4.1 단계별 데이터 처리 상세 (CoT 요약)

### Step 1. 1차 전처리 및 데이터 정규화 (Formatting & Normalization)
1.  **출처 정책 제어**: `catalog/source_registry.json`에 메타 규칙을 선언하여 파이프라인 코드와 출처 설정을 분리하여 확장성 보장.
2.  **텍스트 정제(Cleaning)**: 본문에 섞여 있는 HTML 태그, 이중 공백, 불필요한 이스케이프 문자(`\n`, `\t` 등)를 Regex 필터로 일괄 제거하여 임베딩 시 벡터 왜곡 방지.
3.  **식물 사전 연동**: 수집된 본문 내 단어들을 식물 사전(`data/scripts/common.py`)과 매핑하여 타겟 식물명(`crop_or_plant`) 태그를 명시적으로 주입. (검색 필터 연동용)

### Step 2. 문맥 보존형 단락 분할 (Chunking)
1.  **청크 분할 파라미터**:
    기본값: `max_chars 2200자 / overlap_chars 250자`
    NCPMS 병해충 데이터: `max_chars 1400자 / overlap_chars 160자`
    농사로 실내식물 / 작물 데이터: `max_chars 1200자 / overlap_chars 140자`
                근거: 1. 병해충 문서는 작물명, 병명, 증상, 발생 조건, 예방 정보가 비교적 짧고 밀도가 높음
                    2. 너무 큰 청크로 묶으면 한 chunk 안에 여러 정보가 섞여 검색 초점이 흐려질 수 있음
                    3. 사용자는 보통 “증상”, “발생 조건”, “예방”처럼 구체 질문을 하므로 더 작은 단위가 유리함
                    4. 답변에 citation으로 보여줄 excerpt가 너무 길어지지 않게 하기 위함
                    5. 농사로 관리 문서도 물주기, 광도, 온도, 관리 난이도처럼 항목형 정보가 많아서 짧은 청크가 더 적합함
                    6. HWPX는 표와 문단을 문장형으로 재구성한 문서라, 너무 잘게 잘라 표의 행 맥락이나 작업 일정 흐름이 끊기는 것을 예방하기 위함

2.  **의미 경계 탐색**: 단순 글자 수 컷이 아닌 문장 마침표(`.`)와 개행(`\n`) 경계를 동적으로 추적하여 끊어짐 없는 자연스러운 단락 형성.
3.  **중첩 보존**: 단락 간 경계 부근 지식이 검색 유실되지 않도록 중첩 공간(기본값: 250)을 두어 문맥 연속성(Context Preservation) 유지.

### Step 3. 고밀도 벡터 임베딩 (Vectorization)
1.  **모델**: OpenAI `text-embedding-3-small` (1536 차원 출력).
2.  **가상 시뮬레이션**: 개발 환경 검증용 로컬 해시 모드(`--mode hash`) 탑재로 무결성 테스트 선행 가능.
3.  **물리적 디커플링(Decoupling)**: API 통신 장해 대비 임베딩 데이터를 로컬 파일(`rag_chunks.embedded.jsonl`)로 선 캐싱 후 데이터베이스 적재 진행.

### 💡 4.2 핵심 파라미터 설계 의의 및 RAG 고도화 원리 해설

이해를 돕기 위해 파이프라인 전처리 과정에 적용된 핵심 인자(Parameter)들과 RAG 고도화를 위한 기술적 역할들을 설명합니다.

#### 1. 1차 전처리(정규화) 단계: 식물 사전 필터 (`KNOWN_CROP_OR_PLANT_NAMES` 및 Regex 정제)
*   **어떤 역할을 하나요?**
    *   본문 텍스트 내 지저분한 HTML 태그나 이중 공백을 깨끗하게 청소하고, 식물 이름 목록을 대조하여 해당 글이 어떤 식물(예: `몬스테라`)에 관한 내용인지를 명확하게 찾아냅니다.
*   **왜 RAG 고도화에 중요한가요?**: 
    *   책에 지저분한 낙서나 오타가 묻어있으면 사람이 글을 읽기 힘든 것처럼, AI도 지저분한 특수기호가 제거된 깨끗한 한국어 문장을 주입받아야 텍스트의 본뜻을 오해 없이 판별합니다.
    *   특히 본문에서 식물명을 자동으로 추출하여 메타데이터 필드(`crop_or_plant`)에 미리 담아두면, 나중에 사용자가 AI에게 **"몬스테라 물주기법 알려줘"**라고 물었을 때 AI가 다른 식물(예: `고추`, `토마토`)의 병해충 문서를 헷갈려 호출해서 엉뚱한 대답을 생성하는 **환각(Hallucination) 에러를 가능성을 최소화**할 수 있습니다.

#### 2. 청킹(단락 분할) 단계: 기본 `max_chars=2200` 및 `overlap_chars=250`

*   **어떤 역할을 하나요?**:
    *   수집·정규화된 긴 문서를 한 번에 임베딩하지 않고, 검색과 답변 근거 제시에 적합한 단락 단위로 나누는 단계입니다. 기본 청킹 기준은 `max_chars=2200`, `overlap_chars=250`이며, 문서 성격에 따라 일부 출처는 더 작은 청크 크기를 사용합니다.
    *   NCPMS 병해충 참고 문서는 `max_chars=1400`, `overlap_chars=160`을 적용합니다. 병해충 문서는 작물명, 병해충명, 증상/피해, 발생 조건, 예방 정보가 비교적 짧고 밀도 있게 구성되어 있어, 너무 큰 청크로 묶으면 검색 초점이 흐려질 수 있기 때문입니다.
    *   농사로 실내식물·작물 관리 문서는 `max_chars=1200`, `overlap_chars=140`을 적용합니다. 물주기, 광도, 온도, 관리 난이도처럼 항목형 정보가 많아 비교적 짧은 단위로 나누는 것이 검색 결과와 답변 근거를 더 명확하게 만듭니다.
    *   농사로 작업일정 HWPX 문서(`nongsaro_work_schedule`)는 기본값인 `max_chars=2200`, `overlap_chars=250`을 유지합니다. 표와 문단을 문장형으로 재구성한 문서이기 때문에 지나치게 작게 자르면 작업 일정의 흐름이나 표 행 간 맥락이 끊길 수 있습니다.

*   **왜 RAG 고도화에 중요한가요?**:
    *   **정보 희석 방지**: 너무 긴 문서를 하나의 벡터로 만들면 특정 증상, 관리 조건, 예방 정보가 전체 문맥 속에 묻힐 수 있습니다. 청킹은 사용자의 질문과 직접 관련 있는 부분이 검색될 가능성을 높입니다.
    *   **문맥 손실 완화**: 반대로 문서를 너무 짧게 자르면 문장의 주어, 조건, 결론이 서로 다른 청크로 분리되어 답변 근거로 쓰기 어려워집니다. 현재 파이프라인은 출처별 문서 구조에 맞춰 청크 크기를 조정해 이 균형을 맞춥니다.
    *   **의미 경계 보존**: 청크를 자를 때 단순히 글자 수로 끊지 않고, 문장 마침표(`.`)와 개행(`\n`) 위치를 탐색하여 가능한 한 자연스러운 단락 경계에서 분할합니다.
    *   **중첩 구간 유지**: 청크 사이에는 overlap을 두어, 분할 지점 근처의 키워드나 설명이 검색 과정에서 누락되지 않도록 합니다.

#### 3. 임베딩(벡터화) 단계: `text-embedding-3-small` 모델 및 `1536차원`
*   **어떤 역할을 하나요?**:
    *   텍스트 글자를 사람이 아닌 컴퓨터가 의미론적 유사도로 비교할 수 있도록 다차원 공간의 **수학적 숫자(실수형 벡터 좌표)**로 변환하는 지도 제작 엔진입니다.
*   **왜 RAG 고도화에 중요한가요?**:
    *   **text-embedding-3-small**: OpenAI가 만든 최신 임베딩 렌더러로, 한국어 단어 사이의 아주 세세하고 미묘한 어감 차이(예: "식물이 시들다"와 "식물이 마르다"의 미세한 뉘앙스 차이)를 날카롭고 민감하게 포착해 냅니다.
    *   **1536차원 (Dimensions)**: 단어 하나의 성격을 평가하기 위해 무려 **1,536가지의 세밀한 기준선(수학적 각도)**을 제공하는 것입니다. 설명하는 지표(차원)가 많을수록 단어가 담고 있는 의미의 깊이를 촘촘하게 수치화할 수 있어, 사용자가 어떠한 다양한 일상어 표현으로 질문하더라도 딱 알맞은 핵심 문서를 정확하게 골라내 주는 **유사도 검색(Cosine Similarity)의 정밀도를 완벽에 가깝게 조율**합니다.

---

## 🪴 5. 대상 식물/작물의 단계적 확장 구조
사용자 검색 경험을 점진적으로 확보하기 위해 대상 마스터 리스트를 총 5차 과정에 거쳐 확장하도록 설계했습니다.

```text
  1차 MVP 핵심 실내식물 (몬스테라, 스투키, 금전수, 선인장 등) + 핵심 작물 5종 (토마토, 고추, 상추, 오이, 딸기)
  ⬇
  2차 관엽식물 및 허브류 (벵갈고무나무, 스킨답서스, 알로카시아, 로즈마리, 바질 등)
  ⬇
  3차 텃밭/가정재배 작물 (방울토마토, 파프리카, 감자, 고구마, 가지, 완두 등)
  ⬇
  4차 관상식물 및 화훼류 (장미, 벚나무, 해바라기, 국화, 수국, 카네이션 등)
  ⬇
  5차 공식 OpenAPI 및 도감 기반 추가 대상 확장 (국립수목원 등 반영)
```
*   **특징**: 검색을 위한 "식물 카탈로그 테이블(`plant_master`)"과 상세 대답을 위한 "RAG 근거 문서 테이블(`rag_chunks`)"의 관계를 분리하여, RAG 문서가 부족한 식물도 카탈로그 검색 및 사용자 등록이 원활하게 작동하도록 설계.

---

## 🏆 6. 파이프라인 정합성 최종 검증 결과 (QA)

### 6.1 자동 검증 도구 동작 결과
*   **수행 스크립트**: `validate_processed_data.py`
*   **최종 결과**: **PASS**
*   **주요 통과 기준**:
    *   모든 청크의 `chunk_id`가 고유한 UUID 규격을 따르고 있는지 검증 완료.
    *   각 청크가 `source_id`를 통해 `rag_sources` 테이블과 안정적으로 FK 조인 연결되는지 확인.
    *   임베딩 벡터의 크기가 정확히 `1536` 차원인지 확인 완료.
    *   `pesticide_safety` 카테고리 데이터에 `pesticide_caution` 안전 주의 태그가 강제 주입되었는지 검증 완료.

### 6.2 데이터 소스별 최종 적재량 검증 (Supabase 로드 완료)

*   **전체 적재 완료 청크 수**: **1,682건**
    Supabase `rag_chunks` 테이블 기준, 확인한 출처별 청크 적재량은 다음과 같습니다.
    출처명 및 category 로 구분하였습니다

| 실제 출처 UUID (`source_id`) | 출처 키 (`source_key`) / 출처명 | 적재 수량 | category 구분 | usage_scope |
| :--- | :--- | :---: | :--- | :--- |
| `5ca212d3-9842-5c42-ab5f-089796d177c1` | `ncpms_pest_reference` (NCPMS 병해충 도감/검색 OpenAPI) | 477건 | `pest_reference` | `reference_only` |
| `5d1b013e-d5c5-5bf4-9df7-3b386bdd55ae` | `nongsaro_crop_tech` (농사로 작목정보) | 268건 | `crop_care` | `rag` |
| `94847612-80e8-5db4-8d80-9e25439283ab` | `nongsaro_work_schedule` (농사로 농작업일정) | 235건 | `crop_care` | `rag` |
| `3fe65151-5be8-53bf-bc6c-b1128d78ba15` | `psis_pesticide_safety` (PSIS 농약등록정보 OpenAPI) | 100건 | `pesticide_safety` | `safety_reference_only` |
| `c5430459-dec8-5622-97b8-6553428594f2` | `nongsaro_crop_ebook` (농사로 작목별 농업기술정보 cropEbook) | 100건 | `crop_care` | `rag_and_catalog` |
| `0384cc48-1038-5213-86e2-dbdb2c9c36a6` | `aihub_agriculture_datasets` (AI Hub 농축수산 데이터 목록) | 100건 | `image_reference` | `image_manifest_only` |
| `2d0a2016-f2f1-523b-bd19-e05beac2d904` | `weekly_farming_info` (농사로 주간농사정보) | 100건 | `weekly_farming` | `rag` |
| `b95e6513-4ca9-53d8-88c5-5745662766c6` | `rda_weather365` (농업날씨365) | 100건 | `weather_context` | `context_later` |
| `651507af-3718-5974-87f7-3a77f85290ee` | `naver_encyclopedia` (네이버 지식백과 식물 문서) | 49건 | `plant_reference` | `rag` |
| `834c02cc-a5fe-5bfc-81f0-50d4f0412e93` | `aihub_horticulture_watering_growth` (AI Hub 원예식물 화훼류 물주기/수분공급) | 36건 | `indoor_care` | `rag_and_image_manifest` |
| `50f6d3ff-9aac-5d2a-b9ed-5ea7427533d7` | `national_botanic_garden` (국립수목원 식물도감 및 표준식물목록) | 36건 | `indoor_care` | `rag` |
| `50f6d3ff-9aac-5d2a-b9ed-5ea7427533d7` | `national_botanic_garden` (국립수목원 식물도감 및 표준식물목록) | 35건 | `ornamental_care` | `rag` |
| `50f6d3ff-9aac-5d2a-b9ed-5ea7427533d7` | `national_botanic_garden` (국립수목원 식물도감 및 표준식물목록) | 29건 | `crop_care` | `rag` |
| `55087ab2-5665-5d47-a66a-5e1dd0cd1fe9` | `nongsaro_indoor_catalog` (농사로 실내식물 정보) | 8건 | `indoor_care` | `rag_and_catalog` |
| `367d9495-aa11-52f6-b42e-b97eb6ad79a4` | `aihub_seedling_growth` (AI Hub In-door 육묘작물 생장 데이터) | 7건 | `crop_growth_stage` | `rag_and_image_manifest` |
| `16d08105-0476-5584-9e07-6a91f1e82966` | `ncpms_openapi_guide` (NCPMS OpenAPI 안내) | 2건 | `pest_reference` | `api_contract_reference` |


본 보고서에 명시된 모든 전처리 흐름 및 가공 규격은 수동 검수 및 자동 검증 스크립트를 통해 무결성이 입증되었으며, 원격 Supabase DB 테이블과의 연동 적재가 최종 완수되었습니다.


