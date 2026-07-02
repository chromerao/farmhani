# Data Team 작업 지침서

작성일: 2026-06-29  
목적: `Farm하니? / 식물 주치의 AI`의 1차 MVP에 필요한 데이터 수집, 전처리, RAG 인덱싱 준비 작업을 Data팀이 충돌 없이 진행하기 위한 기준 문서입니다.

## 0. 작업 원칙

- 당장 대용량 데이터를 다운로드하지 않습니다. 먼저 작은 검증용 샘플셋을 만듭니다.
- 원본 데이터, 이미지, PDF, API raw dump, vector DB 파일은 Git에 커밋하지 않습니다.
- 모든 데이터는 출처, URL, 라이선스/이용조건, 수집일, 담당자를 `data/catalog/`에 기록합니다.
- 병해충/농약 데이터는 확정 진단이나 직접 처방처럼 쓰지 않습니다.
- RAG 답변에 들어갈 모든 문서 chunk는 citation으로 추적 가능해야 합니다.

## 1. 이번 주 우선순위

### 1순위: 식물 마스터 데이터

프론트의 `식물 등록`, `식물 검색`, `내 식물 상세` 화면에 바로 필요한 데이터입니다.

가져올 항목:

- 식물명
- 학명
- 영명
- 과명
- 카테고리
- 광도 요구
- 생육형태
- 잎색/잎무늬
- 겨울 최저온도
- 물주기 기준
- 대표 이미지 URL 또는 이미지 출처
- 원문 URL

1차 샘플 목표:

- 실내식물 20종
- 텃밭/작물 5종: 토마토, 고추, 상추, 오이, 딸기

산출물:

- `data/processed/plant_master.sample.jsonl`
- `data/catalog/sources.csv` 갱신

### 2순위: 기본 관리 RAG 문서

AI 상담 답변의 근거로 사용할 공식 문서입니다.

가져올 주제:

- 물주기
- 배수
- 과습
- 건조
- 햇빛/광도
- 통풍
- 온도
- 분갈이
- 잎 황화
- 잎끝 마름
- 시듦

1차 샘플 목표:

- 공식 문서 5~10개
- RAG chunk 30~50개

산출물:

- `data/processed/rag_chunks.sample.jsonl`
- `data/catalog/chunk-schema.md` 기준 준수

### 3순위: 병해충/이상 신호 참고 데이터

1차에서는 진단 모델 학습이 아니라 "의심 신호 분류"와 "주의 문구"에만 사용합니다.

가져올 항목:

- 작물명
- 병해충명
- 증상 설명
- 발생 조건
- 관찰 부위
- 초기 대응 또는 전문가 확인 필요 문구
- 이미지 URL 또는 이미지 출처

1차 샘플 목표:

- 토마토/고추/상추/오이/딸기 중심
- 병해충 또는 생리장해 10~20건

산출물:

- `data/processed/symptom_reference.sample.jsonl`
- `data/processed/image_manifest.sample.csv`

### 4순위: 2차 확장 후보 조사

이번 MVP에 바로 넣지 말고 source catalog만 정리합니다.

- 농업기상
- 병해충 예찰/예측
- 농약안전사용기준
- AI Hub 이미지/생육 데이터
- 스마트팜 생육/환경 데이터

산출물:

- `data/catalog/collection-log.md`에 조사 결과 기록
- 실제 대용량 수집은 팀장 승인 후 진행

## 2. 공식 출처 목록

| 우선순위 | 출처 | 사용 목적 | URL | 작업 메모 |
|---:|---|---|---|---|
| 1 | 농사로 실내식물 정보 | 식물 마스터, 물주기/광도/온도 기준 | https://www.nongsaro.go.kr/portal/ps/psz/psza/contentMain.ps?menuId=PS00376&pageUnit=8 | 실내정원용 식물 검색. 광도 요구, 생육형태, 잎색, 겨울 최저온도, 물주기 조건 확인 가능. |
| 1 | 농사로 작목정보 | 작물별 재배기술, 품종, 병해충 방제 | https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291 | 토마토/고추/상추/오이/딸기부터 제한 수집. |
| 1 | 농사로 메인 | 농업기술, 실내식물 정보, 주간농사정보 진입점 | https://www.nongsaro.go.kr/ | RAG 공식 근거의 기본 출처. |
| 2 | 국가농작물병해충관리시스템 NCPMS | 병해충 도감, 발생정보, 주간농사정보, 예찰/예측 | https://ncpms.rda.go.kr/npms/Main.np | 병해충 데이터는 확정 진단용이 아니라 참고/주의 정보로만 사용. |
| 2 | NCPMS OpenAPI 안내 | 병해충 검색/예측/예찰/상담 OpenAPI | https://ncpms.rda.go.kr/npms/OpenApiInfo.np | API 신청 필요. MVP에서는 문서 조사와 샘플 구조 설계 우선. |
| 3 | 농약안전정보시스템 PSIS | 농약 검색, 안전사용정보, 농약등록정보 | https://psis.rda.go.kr/psis/index.ps | 1차에서는 농약 추천 금지. 안전사용기준 확인과 주의 문구용. |
| 3 | PSIS OpenAPI 안내 | 농약등록정보 OpenAPI | https://psis.rda.go.kr/psis/cont/contentMain.ps?menuId=PS00381 | API key 필요. 서비스코드/요청변수는 사용 전 재확인. |
| 3 | PSIS 농약안전사용기준 | 작물/병해충별 농약 안전사용기준 | https://psis.rda.go.kr/psis/agc/res/agchmRegistStusLst.ps?menuId=PS00263&pageUnit=20 | 직접 처방처럼 노출하지 말고 "라벨/전문가 확인 필요" 태그 필수. |
| 4 | 농업날씨365 | 농업기상, 기상 기반 위험도 확장 | https://weather.rda.go.kr/ | 2차 확장 후보. 지역 기반 알림에 사용 가능. |
| 4 | AI Hub 농축수산 데이터 | 이미지/생육 데이터 후보 조사 | https://www.aihub.or.kr/aihubdata/data/list.do?currMenu=115&srchDataRealmCode=REALM004&topMenu=100 | 대용량 다운로드 전 라이선스와 사용 범위 확인. |

## 3. 전처리 산출물 형식

### `plant_master.sample.jsonl`

프론트 식물 검색과 백엔드 식물 프로필 기본값에 사용합니다.

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
  "leaf_color": ["녹색"],
  "source_id": "nongsaro_indoor_plants",
  "source_url": "https://www.nongsaro.go.kr/...",
  "license": "공공누리 유형 확인 필요",
  "collected_at": "2026-06-29"
}
```

필수 필드:

- `plant_id`
- `name_ko`
- `category`
- `source_id`
- `source_url`
- `license`
- `collected_at`

### `rag_chunks.sample.jsonl`

RAG 검색과 citation에 사용합니다.

```json
{
  "chunk_id": "nongsaro_indoor_water:000001",
  "source_id": "nongsaro_indoor_water",
  "title": "실내식물 물관리",
  "publisher": "농촌진흥청/농사로",
  "url": "https://www.nongsaro.go.kr/...",
  "license": "공공누리 유형 확인 필요",
  "collected_at": "2026-06-29",
  "category": "indoor_care",
  "crop_or_plant": ["실내식물"],
  "symptom_keywords": ["과습", "건조", "잎끝마름"],
  "safety_tags": ["not_diagnosis"],
  "text": "chunk 본문"
}
```

필수 필드:

- `chunk_id`
- `source_id`
- `title`
- `publisher`
- `url`
- `category`
- `symptom_keywords`
- `safety_tags`
- `text`

### `symptom_reference.sample.jsonl`

이미지 분석 결과와 사용자의 증상 텍스트를 RAG query로 변환할 때 참고합니다.

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

이미지 원본은 Git에 넣지 않고 manifest만 관리합니다.

```csv
image_id,storage_path,plant_name,label,status,source_id,source_url,license,usage_scope,notes
sample_001,s3://bucket/path/image.jpg,토마토,잎 황화,abnormal,aihub_crop_disease,https://www.aihub.or.kr/...,확인 필요,reference_only,원본 파일 커밋 금지
```

## 4. 전처리 절차

1. `data/catalog/sources.csv`에 수집 후보를 먼저 등록합니다.
2. 출처 페이지의 이용조건과 라이선스를 확인합니다.
3. 원본 파일은 `data/raw/` 또는 외부 object storage에 저장하고 Git에는 올리지 않습니다.
4. HTML/PDF/API 응답에서 메뉴, 푸터, 광고, 중복 문구를 제거합니다.
5. 표 데이터는 가능한 한 JSON 구조로 보존합니다.
6. 본문 문서는 500~800 token 단위로 chunking합니다.
7. `title`, `publisher`, `url`, `collected_at`, `category`를 모든 chunk에 넣습니다.
8. 식물명 alias를 정리합니다. 예: `방울토마토`, `토마토`, `Tomato`.
9. 증상 키워드를 태깅합니다. 예: `황화`, `시듦`, `잎끝마름`, `반점`, `과습`, `건조`, `해충흔적`.
10. 안전 태그를 넣습니다. 예: `not_diagnosis`, `pesticide_caution`, `expert_check_required`.
11. 샘플 질문으로 검색 품질을 확인합니다.

## 5. 샘플 질문 검수 기준

아래 질문에 대해 관련 chunk가 검색되는지 확인합니다.

- "몬스테라 잎 끝이 갈색으로 말라요."
- "방울토마토 아래쪽 잎이 노랗게 변했어요."
- "고추 잎에 작은 점과 벌레 흔적이 있어요."
- "상추가 축 처지고 흙이 계속 젖어 있어요."
- "오이 잎에 흰 가루 같은 게 보여요."
- "물을 준 지 5일 됐는데 잎이 말라요."

통과 기준:

- 검색 결과에 공식 출처가 포함됩니다.
- 답변 생성용 chunk에 `url` 또는 `source_id`가 있습니다.
- 병해충/농약 관련 결과에는 안전 태그가 있습니다.
- 검색 결과가 부족한 경우 fallback 질문을 만들 수 있습니다.

## 6. Data팀 역할 분담

### Data 담당 A: 식물 마스터/기본 관리 문서

주 작업:

- 농사로 실내식물 정보 조사
- 실내식물 20종 샘플 정리
- 물주기/광도/온도/분갈이 관련 RAG chunk 생성
- `plant_master.sample.jsonl` 작성
- `rag_chunks.sample.jsonl` 1차 작성

### Data 담당 B: 작물/병해충/이미지 후보

주 작업:

- 농사로 작목정보에서 토마토/고추/상추/오이/딸기 조사
- NCPMS 병해충 도감/OpenAPI 후보 조사
- AI Hub 농축수산 이미지/생육 데이터 후보 조사
- `symptom_reference.sample.jsonl` 작성
- `image_manifest.sample.csv` 작성

## 7. Backend/Frontend에 넘길 데이터 계약

Frontend가 바로 필요로 하는 데이터:

- 식물 검색 목록
- 식물 상세 기본 관리 정보
- 대표 이미지 또는 이미지 placeholder
- 카테고리: `indoor`, `vegetable`, `fruit`, `flower`, `succulent`

Backend/RAG가 바로 필요로 하는 데이터:

- RAG chunk JSONL
- source catalog
- 증상 키워드 목록
- safety tag 목록
- citation에 표시할 `title`, `publisher`, `url`

## 8. 완료 조건

1차 Data 샘플셋 완료 조건:

- `plant_master.sample.jsonl`에 최소 25개 식물/작물 포함
- `rag_chunks.sample.jsonl`에 최소 30개 chunk 포함
- 모든 record에 `source_id`, `source_url`, `license`, `collected_at` 포함
- `symptom_reference.sample.jsonl`에 최소 10개 증상 라벨 포함
- `data/catalog/collection-log.md`에 수집/전처리 이력 기록
- Git status에서 원본 대용량 데이터가 추적되지 않음

## 9. 커밋 금지 목록

- AI Hub 원본 이미지
- 사용자 업로드 이미지
- PDF/HWP 원본 대량 파일
- API key가 포함된 요청/응답
- `.env`
- vector DB 파일
- embedding cache
- 모델 weight

## 10. 권장 작업 순서

1. `sources.csv`의 URL/라이선스 빈칸 보강
2. 식물 마스터 25종 수기/반자동 샘플 생성
3. 기본 관리 문서 5~10개 정제
4. RAG chunk 30~50개 생성
5. 증상 라벨 10개 정의
6. 샘플 질문 검색 테스트
7. Backend 담당자에게 JSONL schema 확인 요청
8. 필요 시 OpenAPI 계약에 식물 검색 endpoint 추가 요청
