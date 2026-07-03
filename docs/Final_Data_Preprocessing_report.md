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

## 📂 2. 수집 및 전처리 대상 데이터셋 명세 (총 600건)

RAG 데이터 파이프라인에 주입된 6대 핵심 데이터 출처 명세는 다음과 같습니다.

| 데이터 소스명 | 물리 파일명 (Raw CSV) | 레코드 수 | 카테고리 (Category) | 주요 수집 및 전처리 정보 |
| :--- | :--- | :--- | :--- | :--- |
| **PSIS 농약 정보** | `sample_4_psis_pesticide_60plants_raw.csv` | 100건 | `pesticide_safety` | 작물별 병해충 적용 약제, 희석 배수 및 `pesticide_caution` 안전 문구 강제 적용 |
| **AI Hub 이미지 메타** | `sample_5_image_manifest_60plants_raw.csv` | 100건 | `weather_context` | 실내식물 관수/센서 상태 요약, 육묘장 생육단계 관찰용 보조 텍스트 데이터화 |
| **기상 스트레스 가이드** | `sample_6_weather_disease_risk_60plants_raw.csv` | 100건 | `weather_context` | 기온/광도 조건별 식물 기후 스트레스 지수 및 농가 행동 요령 가이드화 |
| **경기농기원 보고서** | `sample_gyeonggido_agri_pdf_raw.csv` | 100건 | `crop_care` | 경기도농업기술원 발행 실내/원예 식물 연구 PDF 텍스트화 및 핵심 메타 주입 |
| **국립수목원 식물도감** | `sample_national_botanic_garden_raw.csv` | 100건 | `indoor_care` | 식물의 학명, 분류군, 자생지 정보 및 꽃/잎 형태 정보 텍스트 정밀 추출 |
| **농사로 기술 정보** | `sample_nongsaro_crop_tech_raw.csv` | 100건 | `crop_care` | 농촌진흥청 제공 원예특용작물 재배환경, 물관리, 생육단계별 지침서 통합 |

---

## 📐 3. 데이터 구조 및 전처리 파이프라인 설계

### 3.1 디렉토리 아키텍처 (`data/` 구조)
```text
data/
  ├─ catalog/       # 출처 registry(source_registry.json), schema 규격 문서
  ├─ raw/           # Raw CSV, HTML, API raw 응답 등 원천 자료
  ├─ interim/       # 1차 전처리 완료된 중간 산출물 (.normalized.jsonl)
  ├─ processed/     # 2차 청킹 완료된 구조화 데이터 (.sample.jsonl)
  ├─ vectorstore/   # 3차 임베딩(1536차원 벡터) 완료 최종 적재용 데이터 (.embedded.jsonl)
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

### 6.2 데이터 소스별 최종 적재량 검증 (Supabase 로드 완료)
*   **전체 적재 완료 청크 수**: **1,000건** (기존 RAG 데이터 400건 + 신규 5대 소스 500건 + 국립수목원 데이터 100건 완벽 적재 및 공존 중)

| 출처 키 (`source_key`) | 적재 수량 | category 구분 | usage_scope 적용 |
| :--- | :---: | :--- | :--- |
| `psis_pesticide_safety` | 100건 | `pesticide_safety` | `safety_reference_only` |
| `aihub_agriculture_datasets` | 100건 | `weather_context` | `reference_only` |
| `rda_weather365` | 100건 | `weather_context` | `reference_only` |
| `gyeonggido_agri` | 100건 | `crop_care` | `rag` |
| `national_botanic_garden` | 100건 | `indoor_care` | `rag` |
| `nongsaro_crop_tech` | 100건 | `crop_care` | `rag` |

본 보고서에 명시된 모든 전처리 흐름 및 가공 규격은 수동 검수 및 자동 검증 스크립트를 통해 무결성이 입증되었으며, 원격 Supabase DB 테이블과의 연동 적재가 최종 완수되었습니다.
