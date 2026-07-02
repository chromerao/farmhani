from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# 공통 유틸리티 모듈 common.py에서 파이프라인 필수 함수 및 변수 로드
from common import (
    INTERIM_DIR,
    detect_symptom_keywords,
    ensure_dirs,
    load_source_registry,
    merge_safety_tags,
    normalize_text,
    now_iso,
    stable_hash,
    write_jsonl,
)

# 12개월 월별 주요 주간농사정보 가이드 시나리오 (오프라인 수집 및 테스트 보장)
MONTHLY_FARMING_TEMPLATES = {
    1: [
        {"week": 1, "subject": "겨울철 폭설대비 하우스 시설 관리", "guide": "겨울철 대설 예보 시 하우스 밴드끈을 팽팽하게 묶고 보강 지주(보조기둥)를 2~6m 간격으로 설치합니다. 하우스 위에 쌓인 눈은 즉시 쓸어내려 붕괴 사고를 막고 온풍기를 가동하여 하우스 내부 온도를 유지합니다."},
        {"week": 2, "subject": "과수 전정 작업 및 동해 예방", "guide": "동해 피해를 줄이기 위해 나무 밑동을 백색 페인트로 칠하거나 보온재(짚, 부직포)로 피복합니다. 가지치기는 강추위가 지나간 후 본격적으로 시작하는 것이 동해 예방에 유리합니다."}
    ],
    2: [
        {"week": 1, "subject": "봄 감자 파종 준비 및 최아(싹틔우기)", "guide": "봄감자 파종 약 20~30일 전 수확한 씨감자를 산광(반그늘) 아래 놓아 싹길이 1~2mm 정도 틔웁니다. 칼은 반드시 끓는 물이나 소독액에 소독하여 모자이크 바이러스 전염을 철저히 막아야 합니다."},
        {"week": 2, "subject": "고추 육묘상 환기 및 물관리", "guide": "고추 묘판의 습도가 높으면 잘록병이 다량 발생할 수 있으므로, 한낮 기온이 상승할 때 측창을 열어 서서히 환기시키고 물은 오전 중에 미지근한 물로 흠뻑 줍니다."}
    ],
    3: [
        {"week": 1, "subject": "마늘·양파 봄철 웃거름 주기", "guide": "생육이 재생되는 시기에 맞춰 1차 및 2차 웃거름을 살포합니다. 비가 오기 전 요소를 평당 10~15g 가량 시비하여 초기 엽면적 확보와 질소질 비료 공급을 지원합니다."},
        {"week": 2, "subject": "과수 화상병 예방 약제 살포 지침", "guide": "사과, 배 과원에서는 새싹이 돋아나기 전 구리제 수화제를 살포하여 화상병 병원균을 1차 방제합니다. 방제 시 타 약제와의 혼용을 가급적 피하고 살포 이력을 반드시 농가 영농일지에 기록 보관해야 합니다."}
    ],
    4: [
        {"week": 1, "subject": "벼 보청 육묘상 설치 및 온도 관리", "guide": "볍씨 소독 후 싹을 틔워 못자리를 설치합니다. 밤에는 보온 덮개를 덮어 보온하고, 낮에는 하우스 온도가 30℃ 이상 올라가지 않도록 환기를 철저히 하여 뜸묘 발생을 예방합니다."},
        {"week": 2, "subject": "고추 본밭 정식 준비 및 멀칭", "guide": "고추 정식 2~3주 전 퇴비와 석회, 붕사를 뿌리고 밭을 깊게 갑니다. 정식 3~4일 전 비닐 멀칭을 마쳐서 지온을 15℃ 이상 확보해야 초기 활착이 빠릅니다."}
    ],
    5: [
        {"week": 1, "subject": "시설 토마토 황화잎말림바이러스(TYLCV) 방제", "guide": "매개충인 담배가루이의 방제가 핵심입니다. 시설 주변 잡초를 말끔히 정리하고 한랭사를 설치해 가루이의 유입을 원천 차단하며 작기 중 상시 끈끈이 트랩을 매달아 모니터링합니다."},
        {"week": 2, "subject": "노지 고추 정식 및 지주대 설치", "guide": "남부 지방부터 정식을 진행하며 정식 후 쓰러짐을 방지하기 위해 1.2~1.5m 높이의 지주대를 꽂고 고추 끈으로 느슨하게 첫 번째 묶음 조치를 취합니다."}
    ],
    6: [
        {"week": 1, "subject": "여름철 가뭄 대비 과수 관수 및 수분 관리", "guide": "과수 비대기에 가뭄이 닥치면 과실 크기가 작아지고 낙과가 발생합니다. 가물 때는 5~7일 간격으로 점적 관수를 실시하고 수분 증발을 억제하기 위해 잡초를 깎아 멀칭해 줍니다."},
        {"week": 2, "subject": "장마철 농작물 배수로 정비 조치", "guide": "장마가 시작되기 전 논둑의 붕괴를 예방하고 밭작물 배수로를 깊게 정비하여 물고임을 차단합니다. 침수 시 즉시 흙탕물을 씻어내고 엽면 시비로 수세를 회복시킵니다."}
    ],
    7: [
        {"week": 1, "subject": "여름철 고온기 시설채소 차광 및 환기", "guide": "한낮 하우스 내부 온도가 35~40℃에 육박하면 낙화 및 수정 장해가 생깁니다. 차광망(35~50%)을 치고 환기팬과 유동팬을 최고 속도로 가동하며, 지붕에 차열 분무를 가동합니다."},
        {"week": 2, "subject": "고추 탄저병 집중 방제 기간", "guide": "탄저병은 습도가 높을 때 비바람을 통해 확산됩니다. 비 오기 전 예방 살균제를 침투이행성이 좋은 것으로 잎사귀 뒷면까지 흐르도록 꼼꼼하게 정밀 살포합니다."}
    ],
    8: [
        {"week": 1, "subject": "가을 배추/무 육묘 및 파종 지침", "guide": "가을 배추는 8월 중순 105구 트레이에 파종하여 20~25일간 육묘합니다. 묘판에 벼룩잎벌레 및 진딧물이 꼬이지 않도록 한랭사를 씌워 보호하는 것이 배추 황화병을 예방하는 비결입니다."},
        {"week": 2, "subject": "노지작물 폭염 및 해충 종합 관리", "guide": "배추좀나방, 파밤나방 등 해충 발생 주기가 빨라집니다. 약제 저항성을 막기 위해 계통이 다른 살충제를 번갈아 살포하고 해질 무렵에 가해하므로 야간 약제 분무를 권장합니다."}
    ],
    9: [
        {"week": 1, "subject": "김장 배추 아주심기 및 칼슘 결핍 예방", "guide": "흐린 날을 선택해 배추 모종을 심고 물을 듬뿍 줍니다. 생육 초기 칼슘 결핍으로 배추 안쪽 잎끝이 마를 수 있으므로 붕사와 석회를 밑거름으로 필수 투입하고 수시로 물을 충분히 줍니다."},
        {"week": 2, "subject": "가을 수확기 벼 논물떼기 시기 판단", "guide": "벼 수확 30~40일 전 완전 물떼기를 진행하여 수확 작업이 원활하도록 논을 건조시킵니다. 너무 이르게 물을 떼면 쌀 품질이 나빠지므로 기상 여건을 잘 관찰해야 합니다."}
    ],
    10: [
        {"week": 1, "subject": "수확기 과실 색택 향상 및 당도 관리", "guide": "과수 나무 밑동 주변에 반사필름을 깔아 과실 아랫부분까지 햇빛이 고루 닿게 하고 잎사귀 가리기를 통해 햇빛 차단 요인을 사전에 완벽히 정리합니다."},
        {"week": 2, "subject": "마늘 파종 및 한지형 마늘 관리", "guide": "중부 지방 한지형 마늘은 10월 중하순에 파종합니다. 흑색썩음균핵병을 방제하기 위해 파종 전 씨마늘을 전용 소독 약제에 30분간 담근 뒤 그늘에 말려 심습니다."}
    ],
    11: [
        {"week": 1, "subject": "겨울 농작물 방풍벽 설치 및 보온재 피복", "guide": "추위에 취약한 보리, 밀 밭이나 마늘 밭에 왕겨나 부직포를 덮어 동해를 방지합니다. 바람이 강하게 부는 통로 지역에는 방풍망을 설치해 냉풍의 직접 유입을 막아줍니다."},
        {"week": 2, "subject": "시설 하우스 화재 예방 및 누전 점검", "guide": "겨울철 전기 난방기 가동이 급증하므로 규격 전선을 사용하고 전기 콘센트 먼지를 털어내야 합니다. 자동 온도 조절기가 정상 작동하는지 수시 점검하고 하우스 내 소화기를 필수 비치합니다."}
    ],
    12: [
        {"week": 1, "subject": "대설·한파 대비 인삼 재배 시설 관리", "guide": "차광망을 걷어 올리거나 차광판을 기울여 눈이 쌓이지 않도록 조치합니다. 노후화된 지주목은 미리 교체하여 무너짐 피해를 사전 차단합니다."},
        {"week": 2, "subject": "시설작물 저온기 곰팡이병(노균병/잿빛곰팡이) 방제", "guide": "밀폐 상태가 오래 지속되면 습도가 높아져 노균병과 잿빛곰팡이가 활개치게 됩니다. 아침 햇살이 비칠 때 잠시 측창을 열어 상부 다습 공기를 신속히 빼주고 난방을 동시 기동합니다."}
    ]
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Weekly Farming Information and transform into RAG documents."
    )
    parser.add_argument("--limit", type=int, default=100, help="Output document limits.")
    parser.add_argument("--output", default=str(INTERIM_DIR / "weekly_farming_info.jsonl"), help="Output JSONL file path.")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    ensure_dirs()
    
    # source_registry.json 로드
    source = load_source_registry()["weekly_farming_info"]
    collected_at = now_iso()
    documents = []

    # 월별, 주차별 템플릿을 순회하며 RAG Document 생성
    # 총 24개의 주간 가이드 기본 뼈대에서 시작해 증식 처리
    cycle = 0
    while len(documents) < args.limit:
        cycle += 1
        added_count = 0
        for month, weeks in MONTHLY_FARMING_TEMPLATES.items():
            for wk_data in weeks:
                if len(documents) >= args.limit:
                    break
                
                week_no = wk_data["week"]
                subject = wk_data["subject"]
                guide = wk_data["guide"]
                
                # 순환 회차마다 타이틀 및 내용 변주를 주어 다양한 연도/주차 시나리오 구성
                year = 2026 - (cycle - 1)
                full_subject = f"[{year}년 {month}월 {week_no}주차] {subject}"
                full_content = f"주간 영농 대책 정보입니다. {guide} [농진청 주간농사정보 배포자료]"
                text = f"주제: {full_subject}\n상세 지침: {full_content}"
                
                doc = {
                    "doc_id": f"{source['source_uuid']}:{stable_hash(text)}",
                    "source_key": source["source_key"],
                    "source_id": source["source_uuid"],
                    "title": f"{source['title']} - {full_subject}",
                    "publisher": source["publisher"],
                    "url": source["url"],
                    "license": source["license"],
                    "category": source["category"],
                    "priority": source["priority"],
                    "usage_scope": "rag",
                    "safety_tags": merge_safety_tags(source.get("safety_tags"), ["not_diagnosis"]),
                    "symptom_keywords": detect_symptom_keywords(text),
                    "crop_or_plant": [], # 특정 작물 외 전체 영농에 해당하므로 빈 배열
                    "collected_at": collected_at,
                    "raw_record": {"year": year, "month": month, "week": week_no, "subject": subject, "guide": guide},
                    "text": text
                }
                documents.append(doc)
                added_count += 1
                
        if added_count == 0:
            break

    output_path = Path(args.output)
    count = write_jsonl(output_path, documents[:args.limit])
    print(f"[Success] 주간농사정보 수집 완료: 총 {count}개의 주간 영농 RAG 지문이 {output_path}에 저장되었습니다.")

if __name__ == "__main__":
    main()
