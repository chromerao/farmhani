from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from datetime import datetime

# 공통 경로 정의
REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
INTERIM_DIR = REPO_ROOT / "data" / "interim"

def write_jsonl(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)

def convert_special_crops():
    """1. 원예특용작물 기술정보 CSV -> JSONL"""
    csv_path = RAW_DIR / "sample_special_crops_tech_raw.csv"
    if not csv_path.exists():
        print(f"[Skip] {csv_path.name} 파일이 존재하지 않습니다.")
        return
    
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # RAG 임베딩 대상 본문 생성
            text = (
                f"작물(식물)명: {row['plant_name']}\n"
                f"분류: {row['category']}\n"
                f"기술 유형: {row['tech_type']}\n"
                f"제목: {row['title']}\n"
                f"상세 기술 내용:\n{row['content_summary']}"
            )
            rows.append({
                "source_id": "nongsaro_crop_tech",
                "source_key": "nongsaro_crop_tech",
                "title": row["title"],
                "text": text,
                "category": "crop_care",
                "collected_at": row["collected_at"],
                "source_url": row["source_url"],
                "license": row["license"],
                "crop_or_plant": [row["plant_name"]],
                "safety_tags": ["not_diagnosis"]
            })
            
    out_path = INTERIM_DIR / "special_crops_tech.jsonl"
    count = write_jsonl(out_path, rows)
    print(f"[Convert] {csv_path.name} -> {out_path.name} ({count} 건)")

def convert_gyeonggido_agri():
    """2. 경기도농업기술원 보고서 CSV -> JSONL"""
    csv_path = RAW_DIR / "sample_gyeonggido_agri_pdf_raw.csv"
    if not csv_path.exists():
        print(f"[Skip] {csv_path.name} 파일이 존재하지 않습니다.")
        return
        
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"보고서 제목: {row['title']}\n"
                f"관련 작물(식물): {row['plant_name']} ({row['category']})\n"
                f"경기도농업기술원 연구자료 PDF 다운로드 링크: {row['pdf_url']}\n"
                f"연구 보고서 발행 정보 및 작성일: {row['post_date']}"
            )
            rows.append({
                "source_id": "gyeonggido_agri",
                "source_key": "gyeonggido_agri",
                "title": row["title"],
                "text": text,
                "category": "crop_care",
                "collected_at": row["collected_at"],
                "source_url": row["post_url"] or row["source_url"],
                "license": row["license"],
                "crop_or_plant": [row["plant_name"]],
                "safety_tags": ["not_diagnosis"]
            })
            
    out_path = INTERIM_DIR / "gyeonggido_agri_reports.jsonl"
    count = write_jsonl(out_path, rows)
    print(f"[Convert] {csv_path.name} -> {out_path.name} ({count} 건)")

def convert_psis():
    """3. PSIS 농약 가이드라인 CSV -> JSONL"""
    csv_path = RAW_DIR / "sample_4_psis_pesticide_60plants_raw.csv"
    if not csv_path.exists():
        print(f"[Skip] {csv_path.name} 파일이 존재하지 않습니다.")
        return
        
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"대상 작물: {row['crop_name']}\n"
                f"적용 병해충: {row['target_disease_pest']}\n"
                f"농약 용도 분류: {row['pesticide_use']}\n"
                f"약제명(일반명): {row['pesticide_name']} (상표명: {row['brand_name']}, 제조사: {row['company_name']})\n"
                f"사용 방법: {row['use_method']}\n"
                f"희석 배수(량): {row['dilution_ratio']}\n"
                f"안전 사용 기준: {row['safety_standard']}\n"
                f"사용 제한 횟수: {row['use_limit_count']}"
            )
            rows.append({
                "source_id": "psis_pesticide_safety",
                "source_key": "psis_pesticide_safety",
                "title": f"{row['crop_name']} {row['target_disease_pest']} 방제용 농약 안전 사용 가이드라인",
                "text": text,
                "category": "pesticide_safety",
                "collected_at": row["collected_at"],
                "source_url": "https://psis.rda.go.kr/",
                "license": "공공누리 제1유형",
                "crop_or_plant": [row["crop_name"]],
                "safety_tags": ["not_diagnosis", "expert_check_required", "pesticide_caution"]
            })
            
    out_path = INTERIM_DIR / "psis_pesticides.jsonl"
    count = write_jsonl(out_path, rows)
    print(f"[Convert] {csv_path.name} -> {out_path.name} ({count} 건)")

def convert_weather():
    """4. 기상 및 식물 스트레스 지수 CSV -> JSONL"""
    csv_path = RAW_DIR / "sample_6_weather_disease_risk_60plants_raw.csv"
    if not csv_path.exists():
        print(f"[Skip] {csv_path.name} 파일이 존재하지 않습니다.")
        return
        
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"식물(작물)명: {row['crop_name']}\n"
                f"적정 재배 온도 범위: 최저 {row['temp_min_c']}℃ ~ 최고 {row['temp_max_c']}℃\n"
                f"권장 생육 습도: {row['humidity_min_pct']}%\n"
                f"실시간 관측 및 조건: {row['weather_condition']}\n"
                f"기후 위험도 평가: {row['risk_level']} - {row['risk_description']}\n"
                f"농가 행동 지침 및 조치 방안: {row['farm_action_guide']}"
            )
            rows.append({
                "source_id": "rda_weather365",
                "source_key": "rda_weather365",
                "title": f"{row['crop_name']} 환경(기후) 스트레스 감지 경보 및 대응 가이드",
                "text": text,
                "category": "weather_context",
                "collected_at": row["collected_at"],
                "source_url": "https://weather.rda.go.kr/",
                "license": "공공누리 제1유형",
                "crop_or_plant": [row["crop_name"]],
                "safety_tags": ["not_diagnosis"]
            })
            
    out_path = INTERIM_DIR / "weather_risks.jsonl"
    count = write_jsonl(out_path, rows)
    print(f"[Convert] {csv_path.name} -> {out_path.name} ({count} 건)")

def convert_aihub():
    """5. AI Hub 이미지 매니페스트 CSV -> JSONL"""
    csv_path = RAW_DIR / "sample_5_image_manifest_60plants_raw.csv"
    if not csv_path.exists():
        print(f"[Skip] {csv_path.name} 파일이 존재하지 않습니다.")
        return
        
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"식물(작물)명: {row['plant_name']} ({row['category']})\n"
                f"진단 라벨: {row['label']} (상태: {row['status']})\n"
                f"이미지 가상 저장소 경로: {row['storage_path']}\n"
                f"참고 설명: {row['notes']}"
            )
            rows.append({
                "source_id": "aihub_agriculture_datasets",
                "source_key": "aihub_agriculture_datasets",
                "title": f"{row['plant_name']} {row['label']} AI Hub 진단 이미지 정보 카드",
                "text": text,
                "category": "image_reference",
                "collected_at": datetime.now().strftime("%Y-%m-%d"),
                "source_url": "https://aihub.or.kr",
                "license": row["license"],
                "crop_or_plant": [row["plant_name"]],
                "safety_tags": ["not_diagnosis"]
            })
            
    out_path = INTERIM_DIR / "aihub_image_manifest.jsonl"
    count = write_jsonl(out_path, rows)
    print(f"[Convert] {csv_path.name} -> {out_path.name} ({count} 건)")

def convert_national_botanic_garden():
    """6. 국립수목원 식물도감 및 표준식물 목록 CSV -> JSONL"""
    csv_path = RAW_DIR / "sample_national_botanic_garden_raw.csv"
    if not csv_path.exists():
        print(f"[Skip] {csv_path.name} 파일이 존재하지 않습니다.")
        return
        
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"식물명: {row['plant_name']}\n"
                f"학명: {row['scientific_name']} (분류: {row['family_name']} {row['genus_name']})\n"
                f"식물 특징 설명:\n{row['description']}\n"
                f"원산지 및 분포: {row['distribution']}\n"
                f"꽃 특징 정보: {row['flower_info']}\n"
                f"잎 특징 정보: {row['leaf_info']}"
            )
            rows.append({
                "source_id": "national_botanic_garden",
                "source_key": "national_botanic_garden",
                "title": f"{row['plant_name']} 국립수목원 표준 식물도감 명세",
                "text": text,
                "category": "indoor_care" if row["category"] == "실내식물" else ("crop_care" if row["category"] == "작물" else "ornamental_care"),
                "collected_at": row["collected_at"],
                "source_url": row["source_url"],
                "license": row["license"],
                "crop_or_plant": [row["plant_name"]],
                "safety_tags": ["not_diagnosis"]
            })
            
    out_path = INTERIM_DIR / "national_botanic_garden.jsonl"
    count = write_jsonl(out_path, rows)
    print(f"[Convert] {csv_path.name} -> {out_path.name} ({count} 건)")

def main():
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    print("==================================================")
    print("CSV 원시 데이터를 RAG 데이터 파이프라인 JSONL로 변환 시작")
    print("==================================================")
    convert_special_crops()
    convert_gyeonggido_agri()
    convert_psis()
    convert_weather()
    convert_aihub()
    convert_national_botanic_garden()
    print("==================================================")
    print("[Success] 모든 CSV 원시 데이터의 RAG JSONL 변환을 완료하였습니다.")
    print("==================================================")

if __name__ == "__main__":
    main()
