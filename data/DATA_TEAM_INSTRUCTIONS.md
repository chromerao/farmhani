# Data 파트 작업 지시사항

## 목표

Data 파트의 목표는 단순히 샘플 데이터를 몇 개 수집하는 것이 아니라, 이후에도 반복적으로 데이터를 추가 수집할 수 있는 **재사용 가능한 데이터 수집/전처리 파이프라인**을 만드는 것이다.

1차 MVP에서는 아래 세 가지 산출물을 우선 만든다.

- 식물 마스터 데이터
- RAG 문서 chunk 데이터
- 증상/병해충 참고 데이터

대용량 이미지 원본, 원본 PDF, API raw dump, 벡터 DB 파일은 Git에 올리지 않는다.

---

## 1. 우선 수집해야 할 데이터

### 1순위: 농사로 실내식물 정보

사용 목적:

- 프론트의 식물 검색
- 식물 등록 시 품종/카테고리 자동완성
- 식물 상세 페이지의 기본 관리 정보
- RAG 답변의 기본 근거

출처:

- 농사로 실내정원용 식물 검색  
  https://www.nongsaro.go.kr/portal/ps/psz/psza/contentMain.ps?menuId=PS00376&pageUnit=8

확인된 정보:

- 실내정원용 식물 검색 페이지에서 식물명, 학명, 영명 검색 가능
- 광도 요구, 생육형태, 잎색, 잎무늬, 꽃색, 열매색, 꽃피는 계절, 겨울 최저온도, 가격대, 물주기 조건 필터 제공
- 공공누리 유형 또는 이용조건을 반드시 확인해야 함

API 키 필요 여부:

- 웹 페이지 접근 자체는 API 키 없이 가능
- 공식 OpenAPI가 있는지 추가 확인 필요
- 우선은 웹 페이지 구조 분석 후 HTML 기반 수집 또는 수동 샘플 정리로 시작

1차 수집 범위:

- 실내식물 20종
- 예시: 몬스테라, 인도고무나무, 산세베리아, 스킨답서스, 개운죽, 관음죽 등

필수 필드:

- `plant_id`
- `name_ko`
- `name_scientific`
- `name_en`
- `family`
- `category`
- `light_requirement`
- `water_requirement`
- `min_winter_temp_c`
- `growth_form`
- `leaf_color`
- `source_id`
- `source_url`
- `license`
- `collected_at`

---

### 2순위: 농사로 작목정보

사용 목적:

- 텃밭/작물 일부 지원
- 토마토, 고추, 상추, 오이, 딸기 관리 정보
- 작물별 재배 단계, 품종, 병해충 예방 정보
- RAG 답변 근거

출처:

- 농사로 작목정보  
  https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291

API 키 필요 여부:

- 웹 페이지 기반 조회는 API 키 없이 접근 가능
- 공식 OpenAPI 사용 가능 여부는 추가 확인 필요
- 우선 5개 작물만 수동/반자동 수집

1차 수집 작물:

- 토마토
- 고추
- 상추
- 오이
- 딸기

수집 항목:

- 작물명
- 학명 또는 영명
- 재배환경
- 물관리
- 햇빛/온도 조건
- 생육 단계
- 주요 병해충
- 예방/관리 방법
- 출처 URL

---

### 3순위: NCPMS 국가농작물병해충관리시스템

사용 목적:

- 병해충/증상 참고 데이터
- 병해충 도감
- 발생 조건
- 관찰 부위
- 주의 문구
- 2차 확장용 예찰/예측 정보

출처:

- NCPMS 메인  
  https://ncpms.rda.go.kr/npms/Main.np
- NCPMS OpenAPI 안내  
  https://ncpms.rda.go.kr/npms/OpenApiInfo.np

확인할 OpenAPI 종류:

- 병해충 검색 OpenAPI
- 병 상세정보 서비스
- 병원체 검색/상세정보 서비스
- 해충 검색/상세정보 서비스
- 곤충 검색/상세정보 서비스
- 잡초 검색/상세정보 서비스
- 작물 이미지 검색 서비스
- 천적곤충 검색/상세정보 서비스
- 통합검색 서비스
- 병해충 예측 OpenAPI
- 병해충 예찰 OpenAPI
- 병해충 상담 OpenAPI

API 키 필요 여부:

- OpenAPI 사용 전 이용 신청/인증 방식 확인 필요
- 팀원이 NCPMS OpenAPI 안내 페이지에서 신청 절차, 요청 URL, 필수 파라미터를 먼저 정리할 것
- API 키가 발급되기 전에는 웹 공개 도감 페이지 기반으로 샘플 reference만 만든다

1차 사용 범위:

- 병명 확정 진단 금지
- "가능성", "의심", "전문가 확인 필요" 수준의 참고 데이터로만 사용
- 토마토, 고추, 상추, 오이, 딸기 중심으로 10~20개 증상/병해충만 정리

필수 safety tag:

- `not_diagnosis`
- `expert_check_required`
- `pesticide_caution`

---

### 4순위: PSIS 농약안전정보시스템

사용 목적:

- 농약 추천이 아니라 안전사용기준 확인
- 등록 농약 여부
- 사용 시기
- 희석 배수
- 수확 전 안전기간
- 농약 관련 주의 문구

출처:

- PSIS 농약안전정보시스템  
  https://psis.rda.go.kr/psis/index.ps
- PSIS OpenAPI 안내  
  https://psis.rda.go.kr/psis/cont/contentMain.ps?menuId=PS00381

확인된 OpenAPI 정보:

- 농약등록정보 OpenAPI
- 요청 URL: `http://psis.rda.go.kr/openApi/service.do`
- `apiKey` 필수
- `serviceCode` 필수
- 목록 서비스코드 예: `SVC01`
- 상세 서비스코드 예: `SVC02`
- 응답 형식: XML 또는 Ajax 타입 선택

주요 응답 필드:

- 작물명
- 적용병해충
- 용도
- 품목명
- 상표명
- 회사명
- 사용방법
- 희석배수
- 안전사용기준
- 사용횟수

API 키 필요 여부:

- 필요
- `apiKey`는 OpenAPI 이용신청을 통해 받은 key라고 명시되어 있음
- 인증키 미입력 에러 케이스를 처리해야 함

1차 사용 범위:

- MVP 답변에 농약명을 직접 추천하지 않는다
- "농약 사용 전 PSIS에서 등록 여부와 안전사용기준 확인 필요" 문구를 넣는 데 사용
- 실제 API 연동은 2차 또는 팀장 승인 후 진행

---

### 5순위: AI Hub 농축수산 데이터

사용 목적:

- 이미지 참고 데이터
- 증상 taxonomy 보강
- 향후 이미지 모델 학습 후보
- 시연용 정상/이상 이미지 후보

출처:

- AI Hub 농축수산 데이터 목록  
  https://www.aihub.or.kr/aihubdata/data/list.do?currMenu=115&srchDataRealmCode=REALM004&topMenu=100

API 키 필요 여부:

- 데이터 다운로드는 AI Hub 로그인/이용 신청/데이터별 신청 절차가 필요할 가능성이 높음
- AI Hub Open API 사용 가능 여부는 별도 조사 필요
- 당장 대용량 다운로드 금지
- 먼저 데이터셋명, URL, 라이선스, 사용 가능 범위만 catalog에 정리

1차 사용 범위:

- 모델 학습 금지
- 이미지 원본 Git 커밋 금지
- `image_manifest.sample.csv`만 작성

---

### 6순위: 농업날씨365

사용 목적:

- 2차 확장
- 지역 기반 병해충 위험 알림
- 기상 기반 위험도 분석
- 고온다습, 강우, 결로 조건 반영

출처:

- 농업날씨365  
  https://weather.rda.go.kr/

API 키 필요 여부:

- OpenAPI 제공 여부와 인증 방식은 별도 확인 필요
- 1차 MVP에서는 실제 연동하지 않고 후보 조사만 진행

---

## 2. API 키 필요 여부 정리

| 출처 | 우선순위 | API 키 필요 여부 | 이번 단계 작업 |
|---|---:|---|---|
| 농사로 실내식물 웹 페이지 | 1 | 웹 페이지 접근은 불필요 | 20종 샘플 수집 |
| 농사로 작목정보 웹 페이지 | 1 | 웹 페이지 접근은 불필요 | 5개 작물 샘플 수집 |
| 농사로 OpenAPI | 2 | 추가 확인 필요 | API 문서 조사 |
| NCPMS OpenAPI | 2 | 신청/인증 방식 확인 필요 | 병해충 API 목록과 파라미터 조사 |
| PSIS 농약등록정보 OpenAPI | 3 | 필요, `apiKey` 필수 | API 신청 전 문서 정리 |
| AI Hub 데이터 다운로드 | 4 | 로그인/신청 필요 가능성 높음 | 대용량 다운로드 금지, 후보만 정리 |
| AI Hub Open API | 4 | 추가 확인 필요 | API 메뉴 조사 |
| 농업날씨365 | 5 | 추가 확인 필요 | 2차 확장 후보 조사 |

---

## 3. 만들어야 할 데이터 수집 시스템

Data팀은 단발성 수집이 아니라 아래 구조의 파이프라인을 설계한다.

```text
data/
├── catalog/
│   ├── sources.csv
│   ├── collection-log.md
│   └── api-source-map.md
├── raw/
│   └── 원본 저장, Git 커밋 금지
├── interim/
│   └── 중간 정제 결과, Git 커밋 금지
├── processed/
│   ├── plant_master.sample.jsonl
│   ├── rag_chunks.sample.jsonl
│   ├── symptom_reference.sample.jsonl
│   └── image_manifest.sample.csv
└── scripts/
    ├── README.md
    ├── config.py
    ├── collect_nongsaro_indoor.py
    ├── collect_nongsaro_crop.py
    ├── collect_ncpms.py
    ├── collect_psis.py
    ├── normalize_plants.py
    ├── normalize_rag_docs.py
    ├── chunk_documents.py
    └── validate_processed_data.py
```

---

## 4. 코드 구축 지시

### `data/scripts/config.py`

역할:

- 환경변수 로드
- API key 관리
- 경로 상수 관리
- 공통 user-agent 관리

필요 환경변수:

```bash
NONGSARO_API_KEY=
NCPMS_API_KEY=
PSIS_API_KEY=
AIHUB_API_KEY=
WEATHER_API_KEY=
```

주의:

- API key는 `.env`에만 둔다
- 코드에 직접 쓰지 않는다
- `.env`는 Git에 올리지 않는다

---

### `collect_nongsaro_indoor.py`

역할:

- 농사로 실내식물 정보 수집
- 우선 HTML 기반 샘플 수집
- 가능하면 페이지네이션 지원
- 원본 HTML은 `data/raw/nongsaro_indoor/`에 저장
- 정제 전 JSON은 `data/interim/nongsaro_indoor.jsonl`로 저장

최소 기능:

```bash
python data/scripts/collect_nongsaro_indoor.py --limit 25
python data/scripts/collect_nongsaro_indoor.py --all
```

출력 필드:

- `name_ko`
- `name_scientific`
- `name_en`
- `family`
- `light_requirement`
- `water_requirement`
- `min_winter_temp_c`
- `source_url`
- `raw_html_path`
- `collected_at`

---

### `collect_nongsaro_crop.py`

역할:

- 농사로 작목정보 수집
- 토마토, 고추, 상추, 오이, 딸기만 우선 수집
- 작물별 기술정보, 재배환경, 병해충 예방 관련 문서 추출

최소 기능:

```bash
python data/scripts/collect_nongsaro_crop.py --crops 토마토 고추 상추 오이 딸기
```

출력:

- `data/interim/nongsaro_crop_docs.jsonl`

---

### `collect_ncpms.py`

역할:

- NCPMS 병해충 OpenAPI 또는 공개 페이지에서 병해충 reference 수집
- API key가 없으면 실행 시 안내하고 종료
- API key 발급 전에는 수동 조사 결과를 JSONL schema에 맞춰 저장

최소 기능:

```bash
python data/scripts/collect_ncpms.py --crop 토마토
python data/scripts/collect_ncpms.py --crop 고추 --limit 20
```

출력:

- `data/interim/ncpms_pest_reference.jsonl`

필수 safety 처리:

- 모든 record에 `not_diagnosis`
- 농약/방제 관련 내용이 있으면 `pesticide_caution`
- 전문가 확인이 필요한 항목에는 `expert_check_required`

---

### `collect_psis.py`

역할:

- PSIS 농약등록정보 OpenAPI 연동
- `PSIS_API_KEY`가 없으면 실행하지 않음
- 1차 MVP에서는 실제 추천용 데이터로 쓰지 않고 안전사용기준 참고용으로만 저장

최소 기능:

```bash
python data/scripts/collect_psis.py --crop 토마토 --disease 잿빛곰팡이병
```

주의:

- 결과를 사용자 답변에 직접 추천 형태로 노출하지 않는다
- 반드시 `usage_scope: safety_reference_only`로 저장한다

출력:

- `data/interim/psis_pesticide_safety.jsonl`

---

### `normalize_plants.py`

역할:

- 수집된 실내식물/작물 데이터를 `plant_master.sample.jsonl` 형식으로 변환

실행 예:

```bash
python data/scripts/normalize_plants.py \
  --input data/interim/nongsaro_indoor.jsonl \
  --output data/processed/plant_master.sample.jsonl
```

필수 검증:

- `plant_id` 중복 없음
- `name_ko` 존재
- `source_url` 존재
- `license` 존재
- `collected_at` 존재

---

### `normalize_rag_docs.py`

역할:

- 농사로/작목정보/NCPMS 문서를 RAG 문서 원본 형태로 정규화
- 메뉴, 푸터, 중복 텍스트 제거
- 표 데이터는 가능한 JSON 구조로 보존

출력:

- `data/interim/rag_documents.normalized.jsonl`

---

### `chunk_documents.py`

역할:

- 정규화 문서를 500~800 token 단위로 chunking
- 모든 chunk에 citation metadata 포함

실행 예:

```bash
python data/scripts/chunk_documents.py \
  --input data/interim/rag_documents.normalized.jsonl \
  --output data/processed/rag_chunks.sample.jsonl
```

필수 필드:

- `chunk_id`
- `source_id`
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

---

### `validate_processed_data.py`

역할:

- 최종 산출물 검증
- 필수 필드 누락 검사
- 빈 텍스트 검사
- URL 누락 검사
- safety tag 누락 검사
- JSONL 파싱 오류 검사

실행 예:

```bash
python data/scripts/validate_processed_data.py
```

검증 대상:

- `data/processed/plant_master.sample.jsonl`
- `data/processed/rag_chunks.sample.jsonl`
- `data/processed/symptom_reference.sample.jsonl`
- `data/processed/image_manifest.sample.csv`

---

## 5. 최종 산출물 형식

### `plant_master.sample.jsonl`

```json
{
  "plant_id": "indoor_monstera_deliciosa",
  "name_ko": "몬스테라",
  "name_scientific": "Monstera deliciosa",
  "name_en": "Monstera",
  "family": "천남성과",
  "category": ["indoor", "foliage"],
  "light_requirement": "중간 광도",
  "water_requirement": "토양 표면이 말랐을 때 충분히 관수",
  "min_winter_temp_c": 13,
  "growth_form": "덩굴성",
  "source_id": "nongsaro_indoor_plants",
  "source_url": "https://www.nongsaro.go.kr/...",
  "license": "공공누리 유형 확인",
  "collected_at": "2026-06-30"
}
```

### `rag_chunks.sample.jsonl`

```json
{
  "chunk_id": "nongsaro_indoor_water:000001",
  "source_id": "nongsaro_indoor_water",
  "title": "실내식물 물관리",
  "publisher": "농촌진흥청/농사로",
  "url": "https://www.nongsaro.go.kr/...",
  "license": "공공누리 유형 확인",
  "collected_at": "2026-06-30",
  "category": "indoor_care",
  "crop_or_plant": ["실내식물"],
  "symptom_keywords": ["과습", "건조", "잎끝마름"],
  "safety_tags": ["not_diagnosis"],
  "text": "chunk 본문"
}
```

### `symptom_reference.sample.jsonl`

```json
{
  "symptom_id": "leaf_yellowing_lower",
  "label_ko": "하엽 황화",
  "related_keywords": ["잎 노랗게", "아래 잎 노화", "황화"],
  "possible_causes": ["수분 부족", "과습", "질소 부족", "노화"],
  "observation_points": ["흙 표면 수분", "배수구 물빠짐", "최근 물 준 날짜", "햇빛 위치"],
  "risk_level": "medium",
  "safety_tags": ["not_diagnosis"],
  "source_ids": ["nongsaro_indoor_water", "rda_crop_tech"]
}
```

### `image_manifest.sample.csv`

```csv
image_id,storage_path,plant_name,label,status,source_id,source_url,license,usage_scope,notes
sample_001,s3://bucket/path/image.jpg,토마토,잎 황화,abnormal,aihub_crop_disease,https://www.aihub.or.kr/...,확인 필요,reference_only,원본 파일 커밋 금지
```

---

## 6. 이번 주 완료 기준

Data팀은 이번 주 안에 아래까지 완료한다.

- 공식 출처별 API key 필요 여부 정리
- `sources.csv`에 URL, 라이선스, API key 필요 여부, 담당자 기록
- 식물 마스터 25종 샘플 작성
- RAG chunk 30~50개 작성
- 증상 reference 10개 작성
- 데이터 수집/정규화/검증 script 골격 설계
- API key가 없어도 실행 가능한 샘플 수집/정규화 흐름 마련
- 원본 대용량 데이터는 Git에 올리지 않음

---

## 7. 팀장에게 보고할 내용

Data팀은 작업 후 아래를 보고한다.

1. 어떤 출처를 확인했는가
2. API key가 필요한 출처는 어디인가
3. API 신청이 필요한 경우 신청 URL과 필수 파라미터는 무엇인가
4. 샘플 데이터는 몇 건 만들었는가
5. RAG chunk는 몇 개 생성했는가
6. 수집 자동화가 가능한 출처와 수동 정리가 필요한 출처는 어디인가
7. 라이선스 또는 이용조건상 위험한 데이터가 있는가
8. Backend가 바로 사용할 수 있는 JSONL 형식인지 검증했는가

---

## 참고 출처

- 농사로 실내정원용 식물 검색: https://www.nongsaro.go.kr/portal/ps/psz/psza/contentMain.ps?menuId=PS00376&pageUnit=8
- 농사로 작목정보: https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291
- NCPMS OpenAPI 안내: https://ncpms.rda.go.kr/npms/OpenApiInfo.np
- PSIS OpenAPI 안내: https://psis.rda.go.kr/psis/cont/contentMain.ps?menuId=PS00381
- AI Hub 농축수산 데이터: https://www.aihub.or.kr/aihubdata/data/list.do?currMenu=115&srchDataRealmCode=REALM004&topMenu=100
- 농업날씨365: https://weather.rda.go.kr/
