# RAG / LangGraph 설계

## RAG 목표

식물 사진과 재배일지를 공식 원예/농업 자료와 연결해 "현재 상태 해석", "원인 후보", "오늘 할 일", "추가 관찰 포인트", "근거 문서"를 제공합니다.

## 문서 수집/전처리

1. 공식 자료 수집: 농사로, 국립원예특작과학원, 농촌진흥청, 주간농사정보.
2. 원문 보관: PDF/HTML/API raw response는 Git 밖 object storage 또는 로컬 ignored 경로에 저장.
3. 정규화: 제목, URL, 발행기관, 수집일, 라이선스, 카테고리, 작물명, 증상 키워드 추출.
4. 청킹: 문서 구조를 유지하며 500~1000 token 수준으로 분할.
5. 임베딩: chunk와 메타데이터를 pgvector에 저장.
6. 검증: 같은 질문에 대해 출처가 붙는지, 잘못된 확정 진단을 하지 않는지 샘플 테스트.

## LangGraph 노드 초안

| 노드 | 역할 | 입력 | 출력 |
|---|---|---|---|
| `validate_input` | 필수 입력, 파일 형식, 사용자 권한 검증 | 요청 body, JWT | 정규화된 요청 |
| `extract_image_signals` | 사진에서 잎 변색, 시듦, 반점 등 이상 신호 추출 | 이미지 URL | 이미지 관찰 결과 |
| `summarize_user_context` | 식물명, 물 준 날짜, 햇빛, 최근 일지 요약 | DB records | 사용자 맥락 |
| `build_retrieval_query` | 검색 query와 metadata filter 생성 | 관찰 결과, 맥락 | RAG query |
| `retrieve_docs` | 공식 자료 검색 | RAG query | top-k chunks |
| `grade_or_rerank` | 관련도 낮은 chunk 제거 | chunks | filtered chunks |
| `generate_answer` | 상태 요약/오늘 할 일/근거 생성 | context, chunks | draft answer |
| `safety_review` | 확정 진단, 농약 처방, 과장 표현 제거 | draft answer | final answer |
| `persist_result` | 답변과 근거 저장 | final answer | session/message id |

## 답변 정책

- "질병입니다"가 아니라 "질병 가능성이 있습니다", "추가 관찰이 필요합니다"로 표현합니다.
- 농약 관련 정보는 등록 여부, 안전사용기준, 전문가 확인 필요성을 함께 표기합니다.
- 검색 근거가 부족하면 추가 사진, 흙 상태, 배수 상태, 최근 환경 변화를 질문합니다.
- 모든 답변은 최소 1개 이상의 근거 문서 metadata를 포함하는 것을 목표로 합니다.

## 1차 MVP 적용 범위

- 이미지 모델을 직접 학습하기보다 vision model 또는 간단한 증상 태깅으로 시작합니다.
- RAG는 실내식물 물관리/실내정원 유지관리/작목별 농업기술정보를 우선 연결합니다.
- 병해충/농약 데이터는 "주의 정보"와 "전문가 확인 필요" 수준으로 제한합니다.
