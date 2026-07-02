import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

client = OpenAI()

question = "몬스테라는 물을 얼마나 자주 주어야 하나요?"
plant_name = "몬스테라"

wilma_doc = "물주기 봄 여름 가을 겨울 식물의 상세정보 상세정보 분류 잎보기식물 생육형태 직립형 생장높이(cm) 100 실내정원구성 중층목,하층목 골드크레스트 윌마 토양 표면이 말랐을 때 충분히 관수함..."
monstera_doc = "AI Hub 원예식물 생육 라찰 요약: 몬스테라 / 건조\n샘플 수: 11107건\n식물 생태 분류: 습생식물, 건생식물\n토양 상태 라벨: 건조한흙"

def test_prompt(system_prompt):
    print(f"\nTesting prompt:\n{system_prompt}")
    for name, doc in [("골드크레스트 윌마", wilma_doc), ("몬스테라 AI Hub", monstera_doc)]:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"질문: {question}\n대상 식물명: {plant_name}\n\n문서 내용: {doc}"}
            ]
        )
        print(f" -> Doc: {name} => Grader says: {res.choices[0].message.content.strip()}")

prompt_candidate = (
    "사용자의 질문에 답하기 위해 주어진 문서가 관련이 있거나, 질문 대상 식물(몬스테라 등)에 대한 정보(생태 분류, 상태 등)를 포함하여 조금이라도 유용하다면 'yes'를 출력하세요. "
    "만약 대상 식물과 전혀 다른 엉뚱한 식물에 대한 문서라면 'no'를 출력하세요."
)
test_prompt(prompt_candidate)
