from __future__ import annotations

import argparse
import json
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from common import (
    DATA_DIR,
    INTERIM_DIR,
    detect_symptom_keywords,
    ensure_dirs,
    now_iso,
    normalize_text,
    stable_hash,
    write_csv,
    write_jsonl,
)

DEFAULT_INPUT_DIR = DATA_DIR / "external" / "aihub" / "horticulture"
DEFAULT_LABELS_OUTPUT = INTERIM_DIR / "aihub_horticulture_labels.jsonl"
DEFAULT_DOCS_OUTPUT = INTERIM_DIR / "aihub_horticulture_documents.jsonl"
DEFAULT_IMAGE_MANIFEST = INTERIM_DIR / "aihub_horticulture_image_manifest.csv"

SENSOR_FIELDS = [
    "AirTemperature",
    "AirHumidity",
    "Co2",
    "Quantum",
    "SupplyEC",
    "SupplyPH",
    "HighSoilTemp",
    "HighSoilHumi",
    "HighEC",
    "HighPH",
    "LowSoilTemp",
    "LowSoilHumi",
    "LowSoilEC",
    "LowSoilPH",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse AI Hub horticulture label zips into RAG documents and image manifest."
    )
    parser.add_argument("--input", action="append", help="Label zip path or directory. Repeatable.")
    parser.add_argument("--labels-output", default=str(DEFAULT_LABELS_OUTPUT))
    parser.add_argument("--docs-output", default=str(DEFAULT_DOCS_OUTPUT))
    parser.add_argument("--image-manifest-output", default=str(DEFAULT_IMAGE_MANIFEST))
    parser.add_argument("--min-group-size", type=int, default=1)
    return parser.parse_args()


def iter_zip_paths(inputs: list[str] | None) -> list[Path]:
    if not inputs:
        inputs = [str(DEFAULT_INPUT_DIR)]
    paths: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.zip")))
        elif path.is_file() and path.suffix.lower() == ".zip":
            paths.append(path)
    return sorted(set(paths))


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_json_member(zip_path: Path, member: str, data: dict[str, Any]) -> dict[str, Any]:
    info = data.get("info") or {}
    plant = data.get("plant") or {}
    sensor = data.get("sensor") or {}
    watering = data.get("watering") or {}
    pic_info = data.get("picInfo") or data.get("picinfo") or {}

    image_name = pic_info.get("ImageName") or pic_info.get("imageName") or ""
    plant_name = plant.get("PlantName") or ""
    environment = plant.get("Environment") or ""
    soil_state = plant.get("SoilState") or ""
    growth_level = info.get("ResultOfGrowthLevel") or ""

    selected_sensor = {field: as_float(sensor.get(field)) for field in SENSOR_FIELDS if sensor.get(field) is not None}
    text_seed = "|".join([str(zip_path.name), member, image_name, plant_name, environment, soil_state])

    return {
        "record_id": f"aihub_horticulture:{stable_hash(text_seed, 20)}",
        "source_key": "aihub_horticulture_watering_growth",
        "source_file": str(zip_path),
        "json_path": member,
        "image_name": image_name,
        "image_type": pic_info.get("ImageType") or "",
        "captured_at": info.get("GetDateTime") or "",
        "class_id": info.get("ClassID") or "",
        "growth_level": growth_level,
        "place": info.get("Place") or "",
        "plant_name": plant_name,
        "plant_class": plant.get("PlantClass") or "",
        "growth_stage": plant.get("GrowthStage") or "",
        "environment": environment,
        "soil_state": soil_state,
        "root_length": as_float(plant.get("RootLength")),
        "plant_height": as_float(plant.get("PlantHeight")),
        "plant_thickness": as_float(plant.get("PlantThickness")),
        "irrigation_state": watering.get("IrrigationState") or "",
        "watering_time": watering.get("WateringTime") or "",
        "amt_irrigation": as_float(watering.get("AmtIrrigation")),
        "sensor": selected_sensor,
    }


def iter_label_records(zip_paths: Iterable[Path]) -> Iterable[dict[str, Any]]:
    for zip_path in zip_paths:
        with zipfile.ZipFile(zip_path) as zf:
            json_members = [name for name in zf.namelist() if name.lower().endswith(".json")]
            if not json_members:
                print(f"Skipped {zip_path}: no JSON labels found.")
                continue
            for member in json_members:
                with zf.open(member) as f:
                    data = json.loads(f.read().decode("utf-8-sig"))
                yield parse_json_member(zip_path, member, data)


def stat_line(label: str, values: list[float]) -> str | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return f"{label}: 평균 {statistics.mean(clean):.2f}, 범위 {min(clean):.2f}~{max(clean):.2f}"


def most_common(values: Iterable[str]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        if value:
            counts[value] += 1
    return [value for value, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]]


def build_group_docs(records: list[dict[str, Any]], min_group_size: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        plant_name = record.get("plant_name") or "미상"
        environment = record.get("environment") or "환경 미상"
        groups[(plant_name, environment)].append(record)

    docs: list[dict[str, Any]] = []
    collected_at = now_iso()
    for (plant_name, environment), rows in sorted(groups.items()):
        if len(rows) < min_group_size:
            continue

        sensor_values: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            for field, value in (row.get("sensor") or {}).items():
                if value is not None:
                    sensor_values[field].append(value)

        stats = [
            stat_line("공기 온도", sensor_values.get("AirTemperature", [])),
            stat_line("공기 습도", sensor_values.get("AirHumidity", [])),
            stat_line("광량", sensor_values.get("Quantum", [])),
            stat_line("상부 토양 습도", sensor_values.get("HighSoilHumi", [])),
            stat_line("하부 토양 습도", sensor_values.get("LowSoilHumi", [])),
            stat_line("급액 pH", sensor_values.get("SupplyPH", [])),
            stat_line("급액 EC", sensor_values.get("SupplyEC", [])),
        ]
        stats = [line for line in stats if line]

        plant_classes = ", ".join(most_common(row.get("plant_class", "") for row in rows))
        soil_states = ", ".join(most_common(row.get("soil_state", "") for row in rows))
        growth_levels = ", ".join(most_common(row.get("growth_level", "") for row in rows))
        places = ", ".join(most_common(row.get("place", "") for row in rows))
        irrigation_states = ", ".join(most_common(row.get("irrigation_state", "") for row in rows))

        text = normalize_text(
            "\n".join(
                [
                    f"AI Hub 원예식물 생육 라벨 관찰 요약: {plant_name} / {environment}",
                    f"샘플 수: {len(rows)}건",
                    f"식물 생태 분류: {plant_classes or '미상'}",
                    f"촬영/재배 위치: {places or '미상'}",
                    f"토양 상태 라벨: {soil_states or '미상'}",
                    f"생육 상태 라벨: {growth_levels or '미상'}",
                    f"관수 상태 라벨: {irrigation_states or '미상'}",
                    "센서 관찰값: " + ("; ".join(stats) if stats else "제공된 수치 없음"),
                    "이 문서는 원예식물 이미지 라벨과 센서 관찰값을 요약한 참고 자료입니다. 사용자 식물의 상태를 확정 진단하거나 처방하는 기준이 아니라, 물 관리와 생육 환경을 비교하기 위한 보조 근거로 사용해야 합니다.",
                ]
            )
        )

        doc_id = f"aihub_horticulture:{stable_hash(plant_name + '|' + environment, 20)}"
        docs.append(
            {
                "doc_id": doc_id,
                "source_key": "aihub_horticulture_watering_growth",
                "source_id": "aihub_horticulture_watering_growth",
                "title": f"{plant_name} {environment} 생육/관수 라벨 요약",
                "publisher": "AI Hub",
                "url": "https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71705",
                "license": "Dataset-specific approval and terms required",
                "collected_at": collected_at,
                "category": "indoor_care",
                "priority": 2,
                "usage_scope": "rag_and_image_manifest",
                "crop_or_plant": [plant_name],
                "symptom_keywords": detect_symptom_keywords(text),
                "safety_tags": ["not_diagnosis", "observation_reference_only"],
                "text": text,
            }
        )
    return docs


def build_image_manifest(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        rows.append(
            {
                "image_id": stable_hash(record.get("image_name") or record["record_id"], 20),
                "image_name": record.get("image_name", ""),
                "source_file": record.get("source_file", ""),
                "json_path": record.get("json_path", ""),
                "plant_name": record.get("plant_name", ""),
                "plant_class": record.get("plant_class", ""),
                "environment": record.get("environment", ""),
                "soil_state": record.get("soil_state", ""),
                "growth_level": record.get("growth_level", ""),
                "storage_path": "",
                "notes": "AI Hub source image is not committed to Git. Fill storage_path after uploading approved image samples to object storage.",
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    ensure_dirs()
    zip_paths = iter_zip_paths(args.input)
    if not zip_paths:
        raise RuntimeError(f"No label zip files found. Put files under {DEFAULT_INPUT_DIR} or pass --input.")

    records = list(iter_label_records(zip_paths))
    if not records:
        raise RuntimeError("No JSON label records were parsed from the selected zip files.")

    label_count = write_jsonl(Path(args.labels_output), records)
    docs = build_group_docs(records, args.min_group_size)
    doc_count = write_jsonl(Path(args.docs_output), docs)
    manifest_rows = build_image_manifest(records)
    manifest_count = write_csv(
        Path(args.image_manifest_output),
        manifest_rows,
        [
            "image_id",
            "image_name",
            "source_file",
            "json_path",
            "plant_name",
            "plant_class",
            "environment",
            "soil_state",
            "growth_level",
            "storage_path",
            "notes",
        ],
    )

    print(f"Parsed {label_count} AI Hub label records from {len(zip_paths)} zip files.")
    print(f"Wrote {doc_count} RAG summary documents to {args.docs_output}.")
    print(f"Wrote {manifest_count} image manifest rows to {args.image_manifest_output}.")


if __name__ == "__main__":
    main()
