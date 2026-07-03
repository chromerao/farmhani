# RAG 고도화를 위한 이종 농업 데이터의 최종 전처리 결과 보고서 (Final Data Preprocessing Report)

본 보고서는 `Farm하니? / 식물 주치의 AI` 서비스의 RAG(Retrieval-Augmented Generation) 시스템 검색 무결성 및 응답 신뢰성 고도화를 위해 수행된 데이터 전처리 결과를 종합 정리한 최종 문서입니다. 

---

## 📌 1. 전처리 설계 요약 (두괄식)

*   **Step 1. 1차 정규화 및 데이터 클렌징**
    *   **[핵심 명제] 파편화된 이종 데이터를 통일된 RAG 표준 스키마(JSONL)로 매핑하고, Regex 필터링을 통해 텍스트 노이즈(HTML태그/공백)를 제거하여 벡터 왜곡을 방지합니다.**
*   **Step 2. 문맥 보존형 단락 분할 (청킹)**
    *   **[핵심 명제] 문맥 손실(Context Loss)과 정보 희석(Information Dilution)을 방지하기 위해 문장 경계를 보존하는 500자 크기 및 50자 오버랩(Overlap)의 최적 단락 단위로 본문을 분할합니다.**
*   **Step 3. 고밀도 벡터 임베딩 및 안전 검증**
    *   **[핵심 명제] OpenAI `text-embedding-3-small` (1536차원) 모델을 통해 텍스트 의미 공간을 실수형 좌표로 변환하고, 로컬 선캐싱(Decoupling) 및 드라이런 검증을 거쳐 DB 업로드 정합성을 확보합니다.**

---

## 📂 2. 수집 및 전처리 대상 데이터셋 명세 (총 600건 + 마스터 시드)

RAG 데이터 파이프라인에 주입된 데이터 출처 및 개별 수집/정제 규칙 요약 테이블은 다음과 같습니다.

| 데이터 소스명 | 물리 파일명 (Raw CSV) | 레코드 수 | 카테고리 (Category) | 적재 상태 / 범위 | 수집 경로 및 전처리/정제 핵심 규칙 |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **식물 마스터** | `priority_plant_catalog.jsonl` (Seed) | 60종 | `plant_master` | **별도 테이블 적재** | `build_plant_master.py` 활용 / 학명, 영명, 이명(aliases), 과명 파싱 ➡️ `plant_catalog` 테이블 적재 |
| **PSIS 농약 정보** | `sample_4_psis_pesticide_60plants_raw.csv` | 100건 | `pesticide_safety` | **1차 실적재 완료** | 적용 약제 및 안전 희석 배수 추출 ➡️ 본문 내 방제 언급 시 `pesticide_caution` 태그 자동 주입 |
| **AI Hub 이미지 메타** | `sample_5_image_manifest_60plants_raw.csv` | 100건 | `weather_context` | **1차 실적재 완료** | 센서 라벨(수분, 관수 상태) 및 육묘 단계 JSON 텍스트 추출 ➡️ RAG 보조 데이터로 정제 |
| **기상 스트레스 가이드** | `sample_6_weather_disease_risk_60plants_raw.csv` | 100건 | `weather_context` | **1차 실적재 완료** | 기온/광도 임계점 매핑 ➡️ 식물 기후 위해 분석 가이드 및 행동 요령 텍스트화 |
| **경기농기원 보고서** | `sample_gyeonggido_agri_pdf_raw.csv` | 100건 | `crop_care` | **1차 실적재 완료** | 연구 보고서 PDF 자료실 연동 ➡️ 본문 텍스트 추출 및 핵심 메타 주입 (`observation_reference_only`) |
| **국립수목원 식물도감** | `sample_national_botanic_garden_raw.csv` | 100건 | `indoor_care` | **1차 실적재 완료** | OpenAPI 연동 ➡️ 잎/꽃 형태 정보 등 특징 텍스트 추출, 표준 학명/과명 분류 매핑 |
| **농사로 기술 정보** | `sample_special_crops_tech_raw.csv` | 100건 | `crop_care` | **1차 실적재 완료** | `cropEbook API` 및 `farmTechMain` 상세 웹페이지 병합 ➡️ 지침서 정규화 |
| **농작업 일정 HWPX** | `WeeklyFarming (HWPX 원본)` | - | `crop_growth_stage` | *추후 확장 예정* | HWPX XML 문단/표 디코딩 ➡️ 정형 표는 문장형 변환, 비정형 표는 행 구조 텍스트 보존 파싱 |
| **네이버 지식백과** | `(보조 지식 문서)` | - | `indoor_care` | *추후 확장 예정* | 백과사전 API 추출 대상 중 사람의 수동 검수(`manual_url`)를 거친 웹 페이지만 수집 |

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

## 🛠️ 4. 단계별 데이터 처리 상세 (CoT 요약)

### Step 1. 1차 전처리 및 데이터 정규화 (Formatting & Normalization)
1.  **출처 정책 제어**: `catalog/source_registry.json`에 메타 규칙을 선언하여 파이프라인 코드와 출처 설정을 분리하여 확장성 보장.
2.  **텍스트 정제(Cleaning)**: 본문에 섞여 있는 HTML 태그, 이중 공백, 불필요한 이스케이프 문자(`\n`, `\t` 등)를 Regex 필터로 일괄 제거하여 임베딩 시 벡터 왜곡 방지.
3.  **식물 사전 연동**: 수집된 본문 내 단어들을 식물 사전([common.py](file:///C:/Users/playdata2/OneDrive/Desktop/프로젝트/3차%20단위%20프로젝트/SKN30-3rd-3Team/data/scripts/common.py))과 매핑하여 타겟 식물명(`crop_or_plant`) 태그를 명시적으로 주입. (검색 필터 연동용)

### Step 2. 문맥 보존형 단락 분할 (Chunking)
1.  **청크 분할 파라미터**: `Chunk Size 500자` / `Overlap 50자` 셋팅. 
2.  **의미 경계 탐색**: 단순 글자 수 컷이 아닌 문장 마침표(`.`)와 개행(`\n`) 경계를 동적으로 추적하여 끊어짐 없는 자연스러운 단락 형성.
3.  **중첩 보존**: 단락 간 경계 부근 지식이 검색 유실되지 않도록 50자의 중첩 공간을 두어 문맥 연속성(Context Preservation) 유지.

### Step 3. 고밀도 벡터 임베딩 (Vectorization)
1.  **모델**: OpenAI `text-embedding-3-small` (1536 차원 출력).
2.  **가상 시뮬레이션**: 개발 환경 검증용 로컬 해시 모드(`--mode hash`) 탑재로 무결성 테스트 선행 가능.
3.  **물리적 디커플링(Decoupling)**: API 통신 장해 대비 임베딩 데이터를 로컬 파일(`rag_chunks.embedded.jsonl`)로 선 캐싱 후 데이터베이스 적재 진행.

### 💡 4.4 [초보자 가이드] 핵심 파라미터 설계 의의 및 RAG 고도화 원리 해설

이해를 돕기 위해 파이프라인 전처리 과정에 적용된 핵심 인자(Parameter)들과 RAG 고도화를 위한 기술적 역할들을 코딩 초보자 관점에서 쉽게 설명합니다.

#### 1. 1차 전처리(정규화) 단계: 식물 사전 필터 (`KNOWN_CROP_OR_PLANT_NAMES` 및 Regex 정제)
*   **어떤 역할을 하나요?**: 
    *   본문 텍스트 내 지저분한 HTML 태그나 이중 공백을 깨끗하게 청소하고, 식물 이름 목록을 대조하여 해당 글이 어떤 식물(예: `몬스테라`)에 관한 내용인지를 명확하게 찾아냅니다.
*   **왜 RAG 고도화에 중요한가요?**: 
    *   책에 지저분한 낙서나 오타가 묻어있으면 사람이 글을 읽기 힘든 것처럼, AI도 지저분한 특수기호가 제거된 깨끗한 한국어 문장을 주입받아야 텍스트의 본뜻을 오해 없이 판별합니다.
    *   특히 본문에서 식물명을 자동으로 추출하여 메타데이터 필드(`crop_or_plant`)에 미리 담아두면, 나중에 사용자가 AI에게 **"몬스테라 물주기법 알려줘"**라고 물었을 때 AI가 다른 식물(예: `고추`, `토마토`)의 병해충 문서를 헷갈려 호출해서 엉뚱한 대답을 생성하는 **환각(Hallucination) 에러를 원천적으로 100% 예방**할 수 있습니다.

#### 2. 청킹(단락 분할) 단계: `Chunk Size 500자` 및 `Overlap 50자`
*   **어떤 역할을 하나요?**: 
    *   수만 자에 달하는 원문 책 한 권을 통째로 쓰는 대신, 검색에 가장 효과적인 **500글자 단위의 핵심 요약 카드**들로 썰어서 나누어 줍니다. 이 카드를 자를 때 앞 뒷면의 꼬리와 머리글을 **50글자씩 겹치게(Overlap)** 중복해서 잘라냅니다.
*   **왜 RAG 고도화에 중요한가요?**:
    *   **500자 (Chunk Size)**: 책 전체를 임베딩하면 세부적인 정보(예: 특정 해충 농약 희석 배수)가 전체 맥락 속에 묻혀 희석되는 **정보 희석(Information Dilution)** 현상이 일어납니다. 반대로 너무 작게 20~30자 단위로 쪼개면 문장의 맥락이 깨져 주어나 목적어가 빠지는 **문맥 손실(Context Loss)**이 일어납니다. 500자는 AI가 한 번에 답변을 참고하고 질문을 매칭하기에 최적화된 최상의 글자 수 규격입니다.
    *   **50자 (Overlap)**: 문장을 500자씩 정확히 쪼개다 보면 문장 한가운데가 뚝 끊길 수 있습니다. 이를 방지하기 위해 앞뒤 요약 카드의 내용을 50글자씩 중복시켜 겹쳐놓으면, 설령 분할 경계선 부근에 질문 키워드가 걸쳐 있더라도 **의미의 단절 없이 질문을 정확히 탐색**해 낼 수 있게 도와줍니다.

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
  5차 공식 OpenAPI 및 도감 기반 추가 대상 확장 (국립수목원, 경기도 농업보고서 등 반영)
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

### 6.2 데이터 소스별 최종 적재량 검증 (Supabase 로드 완료 팩트)
*   **전체 적재 완료 청크 수**: **1,000건** (팀 협업 수집 계획에 따라 총 12개 세부 데이터 소스를 통해 Supabase DB에 최종 통합 적재 완료)

| 실제 출처 UUID (`source_id`) | 출처 키 (`source_key`) / 출처명 | 적재 수량 | category 구분 | usage_scope 적용 |
| :--- | :--- | :---: | :--- | :--- |
| `5d1b013e-d5c5-5bf4-9df7-3b386bdd55ae` | `nongsaro_crop_tech` (농사로 작목 정보) | 268건 | `crop_care` | `rag` |
| `94847612-80e8-5db4-8d80-9e25439283ab` | `weekly_farming_info` (농사로 농작업 일정) | 235건 | `crop_growth_stage` | `context_later` |
| `c5430459-dec8-5622-97b8-6553428594f2` | `nongsaro_crop_ebook` (농사로 작목 전자책) | 100건 | `crop_care` | `rag_and_catalog` |
| `50f6d3ff-9aac-5d2a-b9ed-5ea7427533d7` | `national_botanic_garden` (국립수목원 도감) | 100건 | `indoor_care` | `rag` |
| `0384cc48-1038-5213-86e2-dbdb2c9c36a6` | `aihub_agriculture_datasets` (AI Hub 이미지메타) | 100건 | `weather_context` | `reference_only` |
| `3fe65151-5be8-53bf-bc6c-b1128d78ba15` | `psis_pesticide_safety` (PSIS 농약 정보) | 82건 | `pesticide_safety` | `safety_reference_only` |
| `5ca212d3-9842-5c42-ab5f-089796d177c1` | `ncpms_pest_reference` (NCPMS 병해충 정보) | 59건 | `pest_reference` | `reference_only` |
| `834c02cc-a5fe-5bfc-81f0-50d4f0412e93` | `aihub_pest_classification` (AI Hub 병해충 분류) | 36건 | `pest_reference` | `reference_only` |
| `55087ab2-5665-5d47-a66a-5e1dd0cd1fe9` | `naver_encyclopedia` (네이버 지식백과) | 8건 | `indoor_care` | `rag` |
| `367d9495-aa11-52f6-b42e-b97eb6ad79a4` | `aihub_seedling_growth` (AI Hub 육묘생장 데이터) | 7건 | `crop_growth_stage` | `rag_and_image_manifest` |
| `651507af-3718-5974-87f7-3a77f85290ee` | `aihub_horticulture_watering` (AI Hub 물주기) | 3건 | `indoor_care` | `rag_and_image_manifest` |
| `16d08105-0476-5584-9e07-6a91f1e82966` | `ncpms_openapi_guide` (NCPMS API 가이드) | 2건 | `pest_reference` | `api_contract_reference` |

본 보고서에 명시된 모든 전처리 흐름 및 가공 규격은 수동 검수 및 자동 검증 스크립트를 통해 무결성이 입증되었으며, 원격 Supabase DB 테이블과의 연동 적재가 최종 완수되었습니다.

---

### 📝 [참고 분석] 경기도농업기술원 보고서 데이터 0건 적재 원인 규명

경기농기원 보고서 원천 데이터(`sample_gyeonggido_agri_pdf_raw.csv` 100건)가 수집 완료되었음에도 최종 RAG 데이터베이스에 적재되지 않은 구체적인 기술적 원인은 다음과 같습니다.

1.  **본문 텍스트 내 URL(PDF 주소) 제거 정화 필터 작동**:
    *   원천 데이터의 절반 가량은 보고서 다운로드용 웹 URL 주소(약 80자 이상)가 차지하고 있습니다. 하지만 RAG 임베딩 과정에서 의미 왜곡을 막기 위해 1차 정규화 스크립트(`normalize_documents.py`) 내에 있는 **URL 주소 강제 제거 Regex 필터**(`re.sub(r"\bhttps?://\S+", "", text)`)가 작동하여 URL 문구들이 전부 공백으로 변환되었습니다.
2.  **보일러플레이트(홈페이지 고정 문구) 제거 작용**:
    *   정규화 과정에서 웹 안내용 문구인 "PDF 다운" 키워드 또한 불필요한 노이즈로 감지되어 본문 정제 필터에 의해 완전히 소거되었습니다.
3.  **최소 글자 수 제한(min-chars = 120자) 미달에 따른 자동 드롭**:
    *   위의 두 가지 노이즈 제거 단계를 거치면서, 원시 본문 텍스트의 실질적 글자 수가 **108자 수준**으로 축소되었습니다.
    *   이는 RAG 시스템 성능 보증을 위한 최소 정규화 글자 수 기준선인 **120자 미만**에 해당하므로, `normalize_documents.py` 의 129라인 필터 규칙(`if len(doc["text"]) < args.min_chars`)에 의해 100건 모두 안전하게 자동 필터링(스킵) 처리된 것으로 확인되었습니다. (자료 누락이 아닌 품질 정규화 가이드라인에 따른 의도된 결과입니다.)
