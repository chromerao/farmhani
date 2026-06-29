import uuid
from fastapi import APIRouter, status
from app.schemas.chat import PlantCareChatRequest, PlantCareChatResponse, Citation

router = APIRouter(prefix="/chat", tags=["Plant Care RAG Chat"])

@router.post("/plant-care", response_model=PlantCareChatResponse, status_code=status.HTTP_200_OK, summary="식물 케어 RAG 상담 실행")
async def consult_plant_care(request: PlantCareChatRequest):
    """
    제공된 식물 ID, 최근 재배 일지, 업로드 사진을 기반으로 공공 원예 문서 RAG 모델을 구동하여 상태 진단 및 처방 가이드를 반환합니다. (Mock 데이터)
    """
    # 사용자의 질문 키워드에 따라 분기하여 적절한 Mock 데이터 응답
    question_lower = request.question.lower()
    
    if "노랗" in question_lower or "yellow" in question_lower or "잎 끝" in question_lower:
        return PlantCareChatResponse(
            summary="과습 또는 질소 부족으로 인한 잎 황화 현상 및 끝마름 증상 의심",
            possibleCauses=[
                "분 흙의 배수 불량 및 잦은 물주기로 인한 뿌리 호흡 장애 (과습)",
                "재배 기간 경과에 따른 토양 내 양분(특히 질소) 결핍",
                "실내 건조로 인한 잎 세포의 부분 탈수"
            ],
            todayActions=[
                "화분 흙의 겉 부분뿐만 아니라 손가락 한 마디 깊이까지 흙이 완전히 말랐는지 확인한 후 물을 주십시오.",
                "화분 밑 물받이에 고인 물은 뿌리 부패를 촉진하므로 즉시 비워주십시오.",
                "실내 습도 유지를 위해 잎 주변에 가볍게 분무를 해주거나 가습기를 가동하십시오."
            ],
            observationChecklist=[
                "새로 돋아나는 잎도 노랗게 변하는지 여부",
                "줄기 밑동 부분이 물러지거나 어두운 갈색으로 변하는지 여부",
                "흙 표면에 곰팡이가 생기거나 퀴퀴한 냄새가 나는지 점검"
            ],
            citations=[
                Citation(
                    sourceId="RAG-DOC-001",
                    title="실내정원 유지관리 가이드라인 - 물관리 요령",
                    url="https://www.nihhs.go.kr",
                    publisher="국립원예특작과학원"
                ),
                Citation(
                    sourceId="RAG-DOC-002",
                    title="농사로 실내식물 생리장해 대처법",
                    url="http://www.nongsaro.go.kr",
                    publisher="농촌진흥청"
                )
            ],
            safetyNotice="본 정보는 공식 문서에 기반한 관리 가이드라인일 뿐이며 특정 식물 병해충에 대한 법적 효력을 가진 확정 진단이 아닙니다. 증상이 지속되거나 악화될 경우 농업기술센터 전문가의 검진을 받으시기 바랍니다."
        )
    
    # 기본 Mock 응답
    return PlantCareChatResponse(
        summary="식물 관리 및 생육 상태 분석 보고",
        possibleCauses=[
            "계절적 환경 변화(조도 부족 또는 급격한 온도 변화)에 따른 적응 반응",
            "토양 영양 불균형 및 환기 부족"
        ],
        todayActions=[
            "통풍이 잘되는 밝은 반음지로 화분을 이동시켜 주십시오.",
            "물주기 전 흙 상태를 반드시 손가락으로 찔러보고 체크하십시오."
        ],
        observationChecklist=[
            "잎 뒷면에 응애나 진딧물 등의 미세 해충이 생겼는지 루페 또는 휴대폰 카메라 줌을 통해 확인하십시오.",
            "주 1회 평균 기온과 환기 횟수를 기록해 두십시오."
        ],
        citations=[
            Citation(
                sourceId="RAG-DOC-999",
                title="도시농업 병해충 및 생리장해 도감",
                url="http://www.nongsaro.go.kr",
                publisher="농촌진흥청"
            )
        ],
        safetyNotice="본 상담 결과는 입력하신 텍스트와 사진에 기반하여 참고용으로 생성되었습니다. 화학 농약을 살포하기 전 반드시 적용 대상을 확인하고 안전사용기준을 준수하십시오."
    )
