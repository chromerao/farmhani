# 농사로/농촌진흥청 작물 5종 데이터 수집 지침서

대상 작물:

- 토마토
- 고추
- 상추
- 오이
- 딸기

목적:

- 식물/작물 관리 AI 서비스의 RAG 원문 데이터 구축
- 작물별 plant master 데이터 구축
- 재배환경, 물관리, 광도, 온도, 생육단계, 병해충, 예방/관리 방법의 공식 출처 기반 정리

작성 기준:

- 농사로/농촌진흥청 공식 OpenAPI 및 공식 웹페이지 기준
- 추측성 정보는 제외
- 공식 문서 또는 공식 페이지에서 확인 가능한 항목만 수집
- API 응답으로 부족한 항목은 공식 웹페이지 또는 공식 PDF/전자책 원문으로 보완

---

## 1. 전체 수집 전략

작물 5개에 대한 데이터를 한 곳에서 완전히 구조화해서 내려주는 단일 API는 확인되지 않았다.

따라서 다음의 3단계 수집 구조를 권장한다.

```text
1단계: 농사로 cropEbook API로 작물 코드, 농업기술길잡이, 목차, 동영상, 품종정보 수집
2단계: 농사로 작물별 공식 상세 페이지에서 작물별 생산기술/병해충/농작업 일정 수집
3단계: NCPMS 및 공공데이터포털 병해충 API로 병해충 상세정보 보강
```

---

## 2. 우선 사용해야 할 공식 API

### 2.1 농사로 작목별 농업기술정보 API

| 항목 | 내용 |
|---|---|
| API 명칭 | 농촌진흥청_작목별농업기술정보 |
| 농사로 서비스명 | `cropEbook` |
| 기존/전환 서비스명 | `cropTechInfo`로 언급됨 |
| 기본 endpoint | `http://api.nongsaro.go.kr/service/cropEbook/{operationName}` |
| 인증키 | 필요 |
| 응답 형식 | XML |
| 주요 용도 | 작목 카테고리, 농업기술길잡이, 목차, 동영상, 품종정보 수집 |

### 2.2 주요 operation

| operation | 설명 | endpoint |
|---|---|---|
| `mainCategoryList` | 대분류 카테고리 조회 | `http://api.nongsaro.go.kr/service/cropEbook/mainCategoryList` |
| `middleCategoryList` | 중분류 카테고리 조회 | `http://api.nongsaro.go.kr/service/cropEbook/middleCategoryList` |
| `subCategoryList` | 소분류/작목명 조회 | `http://api.nongsaro.go.kr/service/cropEbook/subCategoryList` |
| `mainTechList` | 작목기술정보 분류 조회 | `http://api.nongsaro.go.kr/service/cropEbook/mainTechList` |
| `ebookList` | 농업기술길잡이 목록 조회 | `http://api.nongsaro.go.kr/service/cropEbook/ebookList` |
| `cropIndexList` | 농업기술길잡이 목차 조회 | `http://api.nongsaro.go.kr/service/cropEbook/cropIndexList` |
| `videoList` | 동영상 목록 조회 | `http://api.nongsaro.go.kr/service/cropEbook/videoList` |
| `varietyList` | 품종정보 목록 조회 | `http://api.nongsaro.go.kr/service/cropEbook/varietyList` |
| `cropRequestList` | 농업기술길잡이 개정정보 조회 | `http://api.nongsaro.go.kr/service/cropEbook/cropRequestList` |

---

## 3. API 수집 흐름

### 3.1 기본 흐름

```text
mainCategoryList
  ↓
middleCategoryList
  ↓
subCategoryList
  ↓
작물명으로 subCategoryCode 확보
  ↓
ebookList / videoList / varietyList / mainTechList
  ↓
ebookCode, cropsEbookFileNo 확보
  ↓
cropIndexList
  ↓
전자책 URL, 목차, 페이지 정보 수집
```

### 3.2 작물명 검색

`subCategoryList`에서 `subCategoryNm` 파라미터를 사용해 작물명을 검색한다.

예시:

```text
http://api.nongsaro.go.kr/service/cropEbook/subCategoryList?apiKey=YOUR_API_KEY&middleCategoryCode=VC01&subCategoryNm=%ED%86%A0%EB%A7%88%ED%86%A0
```

주의:

- `middleCategoryCode`는 작물 분류에 따라 달라질 수 있다.
- 먼저 `mainCategoryList`, `middleCategoryList`를 호출해 실제 분류 코드를 확인해야 한다.
- 작물명으로 검색해 얻은 `subCategoryCode`를 이후 API 호출의 기준값으로 사용한다.

---

## 4. 작물별 기준 코드 및 공식 상세 페이지

아래 URL은 농사로 작물별 공식 상세 페이지 기준이다.

| 작물명 | 표준품목코드 / subCategoryCode 후보 | 공식 상세 페이지 URL | API 사용 가능 여부 | 주요 수집 가능 정보 |
|---|---|---|---|---|
| 토마토 | `VC010803` | `https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010803` | 가능 | 생산기술, 주요핵심기술, 농작업 일정, 병해충 방제, 동영상, 품종정보 |
| 고추 | `VC011205` | `https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC011205` | 가능 | 생산기술, 주요핵심기술, 농작업 일정, 병해충 방제, 동영상, 품종정보 |
| 상추 | `VC021005` | `https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC021005` | 가능 | 생산기술, 주요핵심기술, 농작업 일정, 병해충 방제, 동영상, 품종정보 |
| 오이 | `VC010901` | `https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010901` | 가능 | 생산기술, 주요핵심기술, 농작업 일정, 병해충 방제, 동영상, 품종정보 |
| 딸기 | `VC010804` | `https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010804` | 가능 | 생산기술, 주요핵심기술, 농작업 일정, 병해충 방제, 동영상, 품종정보 |

주의:

- 위 코드는 농사로 작물 상세 페이지의 `stdPrdlstCode` 기준이다.
- API의 `subCategoryCode`와 동일하게 활용 가능한지 실제 API 응답에서 최종 확인해야 한다.
- 수집 파이프라인에서는 반드시 `subCategoryList`로 작물명 검색 후 API 응답의 코드를 기준값으로 저장한다.

---

## 5. 작물별 API 요청 예시

아래 예시는 `YOUR_API_KEY`를 실제 발급받은 인증키로 교체해야 한다.

### 5.1 토마토

```text
# 작물명 검색
http://api.nongsaro.go.kr/service/cropEbook/subCategoryList?apiKey=YOUR_API_KEY&middleCategoryCode=VC01&subCategoryNm=%ED%86%A0%EB%A7%88%ED%86%A0

# 농업기술길잡이 목록
http://api.nongsaro.go.kr/service/cropEbook/ebookList?apiKey=YOUR_API_KEY&subCategoryCode=VC010803

# 동영상 목록
http://api.nongsaro.go.kr/service/cropEbook/videoList?apiKey=YOUR_API_KEY&subCategoryCode=VC010803&pageNo=1&numOfRows=10

# 품종정보 목록
http://api.nongsaro.go.kr/service/cropEbook/varietyList?apiKey=YOUR_API_KEY&subCategoryCode=VC010803&pageNo=1&numOfRows=10
```

### 5.2 고추

```text
# 작물명 검색
http://api.nongsaro.go.kr/service/cropEbook/subCategoryList?apiKey=YOUR_API_KEY&middleCategoryCode=VC01&subCategoryNm=%EA%B3%A0%EC%B6%94

# 농업기술길잡이 목록
http://api.nongsaro.go.kr/service/cropEbook/ebookList?apiKey=YOUR_API_KEY&subCategoryCode=VC011205

# 동영상 목록
http://api.nongsaro.go.kr/service/cropEbook/videoList?apiKey=YOUR_API_KEY&subCategoryCode=VC011205&pageNo=1&numOfRows=10

# 품종정보 목록
http://api.nongsaro.go.kr/service/cropEbook/varietyList?apiKey=YOUR_API_KEY&subCategoryCode=VC011205&pageNo=1&numOfRows=10
```

### 5.3 상추

```text
# 작물명 검색
http://api.nongsaro.go.kr/service/cropEbook/subCategoryList?apiKey=YOUR_API_KEY&middleCategoryCode=VC02&subCategoryNm=%EC%83%81%EC%B6%94

# 농업기술길잡이 목록
http://api.nongsaro.go.kr/service/cropEbook/ebookList?apiKey=YOUR_API_KEY&subCategoryCode=VC021005

# 동영상 목록
http://api.nongsaro.go.kr/service/cropEbook/videoList?apiKey=YOUR_API_KEY&subCategoryCode=VC021005&pageNo=1&numOfRows=10

# 품종정보 목록
http://api.nongsaro.go.kr/service/cropEbook/varietyList?apiKey=YOUR_API_KEY&subCategoryCode=VC021005&pageNo=1&numOfRows=10
```

### 5.4 오이

```text
# 작물명 검색
http://api.nongsaro.go.kr/service/cropEbook/subCategoryList?apiKey=YOUR_API_KEY&middleCategoryCode=VC01&subCategoryNm=%EC%98%A4%EC%9D%B4

# 농업기술길잡이 목록
http://api.nongsaro.go.kr/service/cropEbook/ebookList?apiKey=YOUR_API_KEY&subCategoryCode=VC010901

# 동영상 목록
http://api.nongsaro.go.kr/service/cropEbook/videoList?apiKey=YOUR_API_KEY&subCategoryCode=VC010901&pageNo=1&numOfRows=10

# 품종정보 목록
http://api.nongsaro.go.kr/service/cropEbook/varietyList?apiKey=YOUR_API_KEY&subCategoryCode=VC010901&pageNo=1&numOfRows=10
```

### 5.5 딸기

```text
# 작물명 검색
http://api.nongsaro.go.kr/service/cropEbook/subCategoryList?apiKey=YOUR_API_KEY&middleCategoryCode=VC01&subCategoryNm=%EB%94%B8%EA%B8%B0

# 농업기술길잡이 목록
http://api.nongsaro.go.kr/service/cropEbook/ebookList?apiKey=YOUR_API_KEY&subCategoryCode=VC010804

# 동영상 목록
http://api.nongsaro.go.kr/service/cropEbook/videoList?apiKey=YOUR_API_KEY&subCategoryCode=VC010804&pageNo=1&numOfRows=10

# 품종정보 목록
http://api.nongsaro.go.kr/service/cropEbook/varietyList?apiKey=YOUR_API_KEY&subCategoryCode=VC010804&pageNo=1&numOfRows=10
```

---

## 6. 농업기술길잡이 원문 수집 절차

### 6.1 `ebookList` 호출

작물별 `subCategoryCode`로 `ebookList`를 호출한다.

```text
http://api.nongsaro.go.kr/service/cropEbook/ebookList?apiKey=YOUR_API_KEY&subCategoryCode={SUB_CATEGORY_CODE}
```

수집해야 할 주요 필드:

| 필드 | 설명 |
|---|---|
| `ebookCode` | 전자책 코드 |
| `ebookName` | 전자책명 |
| `cropsEbookFileNo` | 전자책 파일 번호 |
| `cropsEbookFile` | 전자책 파일 |
| `stdItemCd` | 표준품목코드 |
| `stdItemNm` | 표준품목명 |
| `originFileNm` | 원본 파일명 |

### 6.2 `cropIndexList` 호출

`ebookList`에서 얻은 `ebookCode`, `cropsEbookFileNo`를 사용한다.

```text
http://api.nongsaro.go.kr/service/cropEbook/cropIndexList?apiKey=YOUR_API_KEY&ebookCode={EBOOK_CODE}&cropsEbookFileNo={CROPS_EBOOK_FILE_NO}
```

수집해야 할 주요 필드:

| 필드 | 설명 |
|---|---|
| `ebookUrl` | 전자책 URL |
| `mobileEbookUrl` | 모바일 전자책 URL |
| `cntntsSj` | 목차 제목 |
| `pageNo` | 실제 페이지 번호 |
| `stdItemCd` | 표준품목코드 |
| `stdItemNm` | 표준품목명 |

### 6.3 RAG용 원문 처리

농업기술길잡이 원문은 다음 단위로 나누어 저장한다.

```text
작물명
  └── 농업기술길잡이
        └── 대목차
              └── 중목차
                    └── 소목차
                          └── 본문 chunk
```

권장 chunk 기준:

| 항목 | 권장값 |
|---|---|
| chunk 단위 | 소제목 단위 우선 |
| chunk 길이 | 500~1,200자 |
| overlap | 100~200자 |
| 메타데이터 | crop, source_type, title, section, page, url, license |

---

## 7. 농사로 공식 웹페이지 수집 절차

### 7.1 작물 상세 페이지 URL 구조

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode={STD_PRDLST_CODE}
```

예시:

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010803
```

### 7.2 HTML에서 수집할 항목

농사로 작물 상세 페이지에서 다음 항목을 우선 확인한다.

| 항목 | 수집 목적 |
|---|---|
| 작물명 | plant master 기본값 |
| `stdPrdlstCode` | 작물 식별자 |
| 생산기술 | 재배환경, 재배법, 생육관리 |
| 주요핵심기술 | 핵심 재배 포인트 |
| 농작업 일정 | 생육단계, 시기별 작업 |
| 병해충 방제 | 병해충명, 증상, 방제 방법 |
| 농약정보 | 등록 농약 정보 연결 |
| 동영상 | 보조 학습자료 |
| 품종정보 | 품종 master 구축 |

### 7.3 웹페이지 수집 시 주의사항

- 동적 로딩되는 영역이 있을 수 있으므로 단순 `requests`로 안 잡히는 경우 브라우저 기반 수집이 필요하다.
- URL에 있는 `stdPrdlstCode`를 반드시 메타데이터로 저장한다.
- 페이지별 공공누리 유형 또는 저작권 표시를 별도로 확인한다.
- HTML 본문만 긁지 말고, 제목/탭명/섹션명을 함께 저장해야 RAG 검색 품질이 좋아진다.

---

## 8. 농사로 텃밭 콘텐츠 보조 수집

일부 작물은 농사로의 텃밭가꾸기 콘텐츠에서 학명, 영명, 생육환경이 더 구조적으로 제공된다.

수집 가능성이 높은 항목:

| 항목 | 예시 |
|---|---|
| 학명 | `Lycopersicon esculentum Mill.` |
| 영명 | Tomato |
| 원산지 | 작물별 원산지 |
| 생육 온도 | 싹트는 온도, 잘 자라는 온도 |
| 햇빛 조건 | 햇빛 요구도 |
| 토양 조건 | 토양산도, 토성 |
| 물관리 | 물주기, 관수 조건 |
| 주요 병해충 | 병, 해충, 생리장해 |
| 수확 | 수확 시기, 수확 방법 |

주의:

- 모든 작물이 동일한 구조의 텃밭 콘텐츠를 갖는 것은 아니다.
- 딸기는 동일 구조의 텃밭 상세 페이지가 명확하지 않을 수 있으므로 농업기술길잡이와 작물 상세 페이지를 우선한다.

---

## 9. 병해충 데이터 보강 출처

### 9.1 NCPMS 국가농작물병해충관리시스템

| 항목 | 내용 |
|---|---|
| 기관 | 농촌진흥청 |
| 시스템 | 국가농작물병해충관리시스템, NCPMS |
| 활용 목적 | 작물별 병해충명, 증상, 발생환경, 방제방법 보강 |
| 우선 수집 대상 | 토마토, 고추, 상추, 오이, 딸기 관련 병해충 |

### 9.2 공공데이터포털 병해충 API

공식 출처 후보:

| API 명칭 | 활용 가능 정보 |
|---|---|
| 농촌진흥청_작물 병해충 검색 서비스 | 작물별 병, 해충, 병원체, 잡초, 증상, 방제방법, 사진 |
| 농촌진흥청_병해충 예찰정보 | 병해충 특징, 발생 원인, 방제 방법 |
| 농촌진흥청 병해충발생정보 | 지역별·작물별 병해충 발생정보, 발생 정도, 방제방법 |

### 9.3 병해충 데이터 수집 필드

| 필드 | 설명 |
|---|---|
| `crop_name` | 작물명 |
| `disease_pest_name` | 병해충명 |
| `type` | 병 / 해충 / 병원체 / 잡초 등 |
| `symptom` | 증상 |
| `occurrence_condition` | 발생환경 |
| `prevention` | 예방 방법 |
| `control_method` | 방제 방법 |
| `image_url` | 병해충 이미지 |
| `source_url` | 출처 URL |
| `license` | 이용조건 |

---

## 10. plant master 데이터 스키마

작물별 기본 master 테이블은 아래 구조를 권장한다.

```json
{
  "crop_id": "VC010803",
  "crop_name_ko": "토마토",
  "crop_name_en": "Tomato",
  "scientific_name": "Lycopersicon esculentum Mill.",
  "category": "채소",
  "growth_environment": "",
  "water_management": "",
  "light_condition": "",
  "temperature_condition": "",
  "soil_condition": "",
  "growth_stages": [],
  "major_diseases": [],
  "major_pests": [],
  "prevention_management": "",
  "source_urls": [],
  "license": "",
  "last_collected_at": ""
}
```

### 10.1 필드 정의

| 필드 | 설명 | 우선 출처 |
|---|---|---|
| `crop_id` | 표준품목코드 또는 API subCategoryCode | 농사로 작물 상세 페이지, `subCategoryList` |
| `crop_name_ko` | 작물명 | 농사로 작물 상세 페이지 |
| `crop_name_en` | 영명 | 농사로 텃밭 콘텐츠, 농업기술길잡이 |
| `scientific_name` | 학명 | 농사로 텃밭 콘텐츠, 농업기술길잡이 |
| `category` | 작물 분류 | `mainCategoryList`, `middleCategoryList` |
| `growth_environment` | 재배환경 | 농업기술길잡이, 생산기술 |
| `water_management` | 물관리 | 농업기술길잡이, 텃밭 콘텐츠 |
| `light_condition` | 햇빛/광도 조건 | 텃밭 콘텐츠, 농업기술길잡이 |
| `temperature_condition` | 온도 조건 | 텃밭 콘텐츠, 농업기술길잡이 |
| `soil_condition` | 토양 조건 | 텃밭 콘텐츠, 농업기술길잡이 |
| `growth_stages` | 생육단계 | 농작업 일정, 농업기술길잡이 |
| `major_diseases` | 주요 병 | 농사로 병해충 방제, NCPMS |
| `major_pests` | 주요 해충 | 농사로 병해충 방제, NCPMS |
| `prevention_management` | 예방/관리 방법 | 농사로 병해충 방제, NCPMS |
| `source_urls` | 출처 URL 목록 | 모든 수집 원문 |
| `license` | 이용조건 | 페이지 하단 또는 공공데이터포털 |
| `last_collected_at` | 수집일 | 내부 메타데이터 |

---

## 11. RAG 문서 스키마

RAG용 문서는 plant master와 분리해서 저장한다.

```json
{
  "doc_id": "tomato_guide_001",
  "crop_id": "VC010803",
  "crop_name": "토마토",
  "source_type": "농업기술길잡이",
  "title": "토마토 재배기술",
  "section_path": ["재배", "생육관리", "온도관리"],
  "content": "본문 chunk",
  "page": 12,
  "source_url": "https://...",
  "license": "공공누리 유형 확인 필요",
  "collected_at": "YYYY-MM-DD"
}
```

### 11.1 RAG 문서 분류 태그

| 태그 | 의미 |
|---|---|
| `basic_info` | 작물 기본정보 |
| `environment` | 재배환경 |
| `water` | 물관리 |
| `light` | 햇빛/광도 |
| `temperature` | 온도 |
| `soil` | 토양 |
| `growth_stage` | 생육단계 |
| `disease` | 병 |
| `pest` | 해충 |
| `prevention` | 예방 |
| `control` | 방제 |
| `fertilizer` | 비료 |
| `harvest` | 수확 |
| `variety` | 품종 |

---

## 12. 작물별 수집 체크리스트

### 12.1 토마토

| 수집 항목 | 우선 출처 | 상태 |
|---|---|---|
| 작물명 | 농사로 작물 상세 페이지 | 수집 대상 |
| 학명/영명 | 농사로 텃밭 콘텐츠 또는 농업기술길잡이 | 수집 대상 |
| 재배환경 | 농업기술길잡이 | 수집 대상 |
| 물관리 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 햇빛/광도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 온도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 생육단계 | 농작업 일정 / 농업기술길잡이 | 수집 대상 |
| 병해충 | 농사로 병해충 방제 / NCPMS | 수집 대상 |
| 예방/관리 | 농사로 병해충 방제 / NCPMS | 수집 대상 |

공식 상세 페이지:

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010803
```

### 12.2 고추

| 수집 항목 | 우선 출처 | 상태 |
|---|---|---|
| 작물명 | 농사로 작물 상세 페이지 | 수집 대상 |
| 학명/영명 | 농사로 텃밭 콘텐츠 또는 농업기술길잡이 | 수집 대상 |
| 재배환경 | 농업기술길잡이 | 수집 대상 |
| 물관리 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 햇빛/광도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 온도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 생육단계 | 농작업 일정 / 농업기술길잡이 | 수집 대상 |
| 병해충 | 농사로 병해충 방제 / NCPMS | 수집 대상 |
| 예방/관리 | 농사로 병해충 방제 / NCPMS | 수집 대상 |

공식 상세 페이지:

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC011205
```

### 12.3 상추

| 수집 항목 | 우선 출처 | 상태 |
|---|---|---|
| 작물명 | 농사로 작물 상세 페이지 | 수집 대상 |
| 학명/영명 | 농사로 텃밭 콘텐츠 또는 농업기술길잡이 | 수집 대상 |
| 재배환경 | 농업기술길잡이 | 수집 대상 |
| 물관리 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 햇빛/광도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 온도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 생육단계 | 농작업 일정 / 농업기술길잡이 | 수집 대상 |
| 병해충 | 농사로 병해충 방제 / NCPMS | 수집 대상 |
| 예방/관리 | 농사로 병해충 방제 / NCPMS | 수집 대상 |

공식 상세 페이지:

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC021005
```

### 12.4 오이

| 수집 항목 | 우선 출처 | 상태 |
|---|---|---|
| 작물명 | 농사로 작물 상세 페이지 | 수집 대상 |
| 학명/영명 | 농사로 텃밭 콘텐츠 또는 농업기술길잡이 | 수집 대상 |
| 재배환경 | 농업기술길잡이 | 수집 대상 |
| 물관리 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 햇빛/광도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 온도 | 농업기술길잡이 / 텃밭 콘텐츠 | 수집 대상 |
| 생육단계 | 농작업 일정 / 농업기술길잡이 | 수집 대상 |
| 병해충 | 농사로 병해충 방제 / NCPMS | 수집 대상 |
| 예방/관리 | 농사로 병해충 방제 / NCPMS | 수집 대상 |

공식 상세 페이지:

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010901
```

### 12.5 딸기

| 수집 항목 | 우선 출처 | 상태 |
|---|---|---|
| 작물명 | 농사로 작물 상세 페이지 | 수집 대상 |
| 학명/영명 | 농업기술길잡이 / RDA 자료 | 수집 대상 |
| 재배환경 | 농업기술길잡이 | 수집 대상 |
| 물관리 | 농업기술길잡이 | 수집 대상 |
| 햇빛/광도 | 농업기술길잡이 | 수집 대상 |
| 온도 | 농업기술길잡이 | 수집 대상 |
| 생육단계 | 농작업 일정 / 농업기술길잡이 | 수집 대상 |
| 병해충 | 농사로 병해충 방제 / NCPMS | 수집 대상 |
| 예방/관리 | 농사로 병해충 방제 / NCPMS | 수집 대상 |

공식 상세 페이지:

```text
https://www.nongsaro.go.kr/portal/farmTechMain.ps?menuId=PS65291&stdPrdlstCode=VC010804
```

---

## 13. 라이선스 및 이용조건 처리

### 13.1 필수 저장 항목

각 원문 또는 API 응답마다 아래 정보를 저장한다.

| 필드 | 설명 |
|---|---|
| `source_name` | 농사로, 농촌진흥청, 공공데이터포털, NCPMS 등 |
| `source_url` | 실제 수집 URL |
| `api_endpoint` | API endpoint |
| `license_type` | 공공누리 유형 또는 이용허락범위 |
| `commercial_use` | 상업적 이용 가능 여부 |
| `modification_allowed` | 변경 가능 여부 |
| `attribution_required` | 출처표시 필요 여부 |
| `checked_at` | 라이선스 확인일 |

### 13.2 주의사항

- 농사로 OpenAPI 목록에서 작목별농업기술정보는 공공누리 유형 표시가 있으므로 반드시 확인 후 저장한다.
- 개별 농사로 웹 콘텐츠는 페이지마다 공공누리 유형이 다를 수 있다.
- 공공누리 제3유형, 제4유형은 상업적 이용 또는 변경 가능 여부에 제한이 있으므로 RAG 서비스 공개 시 주의해야 한다.
- 원문을 그대로 재배포하는 기능은 피하고, 출처 URL과 요약/근거 인용 중심으로 설계한다.

---

## 14. 최종 수집 우선순위

### 1순위: 작물 식별자 확보

```text
subCategoryList → 작물명 검색 → subCategoryCode 저장
```

### 2순위: 농업기술길잡이 확보

```text
ebookList → cropIndexList → ebookUrl / 목차 / 페이지 정보 저장
```

### 3순위: 작물 상세 페이지 수집

```text
farmTechMain.ps?stdPrdlstCode={CODE}
```

### 4순위: 병해충 보강

```text
NCPMS / 공공데이터포털 병해충 API
```

### 5순위: plant master 구조화

```text
작물명, 학명, 영명, 재배환경, 물관리, 광도, 온도, 생육단계, 병해충, 예방/관리, 출처, 라이선스
```

---

## 15. 개발 구현 순서

### 15.1 API 키 발급 전

API 키가 없을 때는 공식 웹페이지 중심으로 먼저 수집한다.

```text
1. 작물별 farmTechMain URL 저장
2. HTML에서 탭/제목/본문 링크 추출
3. 농업기술길잡이 또는 생산기술 링크 수집
4. 병해충 방제 링크 수집
5. 수집 URL과 라이선스 메타데이터 저장
```

### 15.2 API 키 발급 후

API 기반으로 정규화한다.

```text
1. mainCategoryList 호출
2. middleCategoryList 호출
3. subCategoryList에서 5개 작물 검색
4. 응답의 subCategoryCode를 확정값으로 저장
5. ebookList 호출
6. cropIndexList 호출
7. videoList 호출
8. varietyList 호출
9. NCPMS 병해충 API 호출
10. plant master와 RAG 문서를 분리 저장
```

---

## 16. 저장 파일 구조 예시

```text
data/
  raw/
    nongsaro/
      crop_ebook/
        tomato/
        pepper/
        lettuce/
        cucumber/
        strawberry/
      farmtech_pages/
        tomato.html
        pepper.html
        lettuce.html
        cucumber.html
        strawberry.html
    ncpms/
      tomato_disease_pest.json
      pepper_disease_pest.json
      lettuce_disease_pest.json
      cucumber_disease_pest.json
      strawberry_disease_pest.json

  processed/
    plant_master.csv
    plant_master.json
    rag_documents.jsonl
    disease_pest_master.csv

  metadata/
    source_license.csv
    collection_log.csv
```

---

## 17. 최소 MVP 수집 범위

처음부터 모든 원문을 다 긁지 말고, 아래 범위부터 수집한다.

| 우선순위 | 데이터 | 이유 |
|---:|---|---|
| 1 | 작물별 공식 상세 페이지 URL | 작물 식별자와 공식 출처 확보 |
| 2 | 농업기술길잡이 목차/전자책 URL | RAG 핵심 원문 |
| 3 | 농작업 일정 | 생육단계/관리 행동 추천에 필요 |
| 4 | 병해충 방제 | 식물 관리 AI의 핵심 기능 |
| 5 | 학명/영명/환경조건 | plant master 기본값 |
| 6 | 품종정보 | 2차 확장용 |
| 7 | 동영상 | 보조 자료 |

---

## 18. 주의할 점

- `subCategoryCode`와 `stdPrdlstCode`가 항상 완전히 동일하다고 가정하지 말고, API 응답에서 재확인한다.
- 농사로 상세 페이지는 동적 로딩 영역이 있을 수 있으므로 HTML 파싱 실패 시 브라우저 자동화 수집을 고려한다.
- API 응답의 XML 필드명과 웹페이지 HTML 섹션명은 별도 매핑 테이블로 관리한다.
- 병해충 정보는 농사로와 NCPMS 양쪽에서 중복될 수 있으므로 병해충명 정규화가 필요하다.
- RAG에 넣을 본문은 반드시 출처 URL, 페이지, 섹션명을 함께 저장한다.
- 라이선스는 데이터셋 단위가 아니라 원문 페이지 단위로 확인한다.

---

## 19. 결론

작물 5개 데이터 수집은 다음 조합이 가장 안정적이다.

```text
농사로 cropEbook API
+ 농사로 작물별 farmTechMain 공식 상세 페이지
+ 농사로 농업기술길잡이 전자책
+ NCPMS/공공데이터포털 병해충 API
```

이 구조를 사용하면 다음 데이터를 확보할 수 있다.

- 작물명
- 작물 코드
- 학명/영명
- 재배환경
- 물관리
- 햇빛/광도 조건
- 온도 조건
- 생육 단계
- 주요 병해충
- 예방/관리 방법
- 출처 URL
- 라이선스/이용조건

단, 모든 항목이 하나의 API에서 구조화되어 내려오지는 않으므로, API 수집 + 공식 웹페이지 파싱 + 원문 RAG chunking을 함께 수행해야 한다.
