from __future__ import annotations

import argparse
import json
import re
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

DEFAULT_INPUT_DIR = DATA_DIR / "external" / "aihub" / "seedling_growth"
DEFAULT_LABELS_OUTPUT = INTERIM_DIR / "aihub_seedling_growth_labels.jsonl"
DEFAULT_DOCS_OUTPUT = INTERIM_DIR / "aihub_seedling_growth_documents.jsonl"
DEFAULT_IMAGE_MANIFEST = INTERIM_DIR / "aihub_seedling_growth_image_manifest.csv"

CROP_BY_CODE = {
    "1": "고추",
    "2": "토마토",
    "3": "파프리카",
    "4": "배추",
    "5": "상추",
    "6": "양배추",
}
STAGE_BY_CODE = {
    "2": "떡잎",
    "3": "본엽2매",
    "4": "본엽4매~8매",
    "5": "본엽8매~10매",
    "6": "분지발생",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse AI Hub In-door seedling growth label zips into RAG documents and image manifest."
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


def infer_crop_stage(zip_path: Path, member: str) -> tuple[str, str]:
    text = f"{zip_path.name}/{member}"
    crop = ""
    stage = ""

    code_match = re.search(r"[TV]L[_-](\d+)\.[^_/\\]+[_-](\d+)\.", text)
    if code_match:
        crop = CROP_BY_CODE.get(code_match.group(1), "")
        stage = STAGE_BY_CODE.get(code_match.group(2), "")

    for value in CROP_BY_CODE.values():
        if value in text:
            crop = value
            break
    for value in ["화방발생", "분지발생", "본엽8매~10매", "본엽4매~8매", "본엽4매", "본엽2매", "떡잎"]:
        if value in text:
            stage = value
            break

    if crop == "토마토" and stage == "본엽8매~10매":
        stage = "화방발생"
    return crop or "작물 미상", stage or "생장단계 미상"


def listify(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def first_text(*values: Any) -> str:
    for value in values:
        if value not in (None, "", []):
            return str(value)
    return ""


def collect_class_names(data: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ["class", "classes", "categories"]:
        for row in listify(data.get(key)):
            if isinstance(row, dict):
                name = first_text(row.get("name"), row.get("label"), row.get("value"))
                if name and name not in names:
                    names.append(name)
    return names


def annotation_counts(data: dict[str, Any]) -> dict[str, int]:
    annotations = listify(data.get("annotations") or data.get("annotation") or data.get("objects"))
    bbox_count = 0
    polygon_count = 0
    for ann in annotations:
        if not isinstance(ann, dict):
            continue
        if ann.get("bbox") or ann.get("bounding_box") or ann.get("box"):
            bbox_count += 1
        if ann.get("segmentation") or ann.get("polygon") or ann.get("points"):
            polygon_count += 1
    return {
        "annotation_count": len(annotations),
        "bbox_count": bbox_count,
        "polygon_count": polygon_count,
    }


def image_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_images = data.get("images") or data.get("image") or {}
    rows = listify(raw_images)
    if rows:
        return [row for row in rows if isinstance(row, dict)]
    return [{}]


def parse_json_member(zip_path: Path, member: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    crop, stage = infer_crop_stage(zip_path, member)
    classes = collect_class_names(data)
    counts = annotation_counts(data)
    rows = []
    for image in image_rows(data):
        file_name = first_text(
            image.get("file_name"),
            image.get("filename"),
            image.get("name"),
            image.get("image_name"),
            image.get("id"),
        )
        captured_at = first_text(image.get("date"), image.get("datetime"), image.get("created_at"))
        location = first_text(image.get("shoot_location"), image.get("location"), image.get("place"))
        view = first_text(image.get("shoot_view"), image.get("view"), image.get("angle"))
        seedbed = first_text(image.get("seedbed"), image.get("tray"), image.get("bed"))
        text_seed = "|".join([zip_path.name, member, file_name, crop, stage])
        rows.append(
            {
                "record_id": f"aihub_seedling_growth:{stable_hash(text_seed, 20)}",
                "source_key": "aihub_seedling_growth",
                "source_file": str(zip_path),
                "json_path": member,
                "image_name": file_name,
                "captured_at": captured_at,
                "shoot_location": location,
                "shoot_view": view,
                "seedbed": seedbed,
                "crop_name": crop,
                "growth_stage": stage,
                "class_names": classes,
                **counts,
            }
        )
    return rows


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
                yield from parse_json_member(zip_path, member, data)


def most_common(values: Iterable[str]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        if value:
            counts[value] += 1
    return [value for value, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]]


def build_group_docs(records: list[dict[str, Any]], min_group_size: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record.get("crop_name") or "작물 미상", record.get("growth_stage") or "생장단계 미상")].append(record)

    docs: list[dict[str, Any]] = []
    collected_at = now_iso()
    for (crop, stage), rows in sorted(groups.items()):
        if len(rows) < min_group_size:
            continue
        annotation_count = sum(int(row.get("annotation_count") or 0) for row in rows)
        bbox_count = sum(int(row.get("bbox_count") or 0) for row in rows)
        polygon_count = sum(int(row.get("polygon_count") or 0) for row in rows)
        class_names = []
        for row in rows:
            for name in row.get("class_names") or []:
                if name and name not in class_names:
                    class_names.append(name)

        locations = ", ".join(most_common(row.get("shoot_location", "") for row in rows))
        views = ", ".join(most_common(row.get("shoot_view", "") for row in rows))
        classes = ", ".join(class_names[:12]) or "라벨 클래스 미상"
        text = normalize_text(
            "\n".join(
                [
                    f"AI Hub In-door 육묘장 생장 라벨 요약: {crop} / {stage}",
                    f"샘플 이미지/라벨 수: {len(rows)}건",
                    f"객체 annotation 수: {annotation_count}건",
                    f"바운딩박스 annotation 수: {bbox_count}건",
                    f"폴리곤 annotation 수: {polygon_count}건",
                    f"주요 라벨 클래스: {classes}",
                    f"촬영 위치: {locations or '미상'}",
                    f"촬영 각도: {views or '미상'}",
                    "이 문서는 실내/시설 육묘장 이미지 라벨을 작물과 생장단계 기준으로 요약한 참고 자료입니다. 사용자의 작물이 어느 생장단계에 가까운지 설명하거나, 잎 수/형태 관찰을 요청하는 보조 근거로만 사용해야 합니다.",
                ]
            )
        )
        symptom_keywords = detect_symptom_keywords(text)
        if "growth_stage" not in symptom_keywords:
            symptom_keywords.append("growth_stage")
        docs.append(
            {
                "doc_id": f"aihub_seedling_growth:{stable_hash(crop + '|' + stage, 20)}",
                "source_key": "aihub_seedling_growth",
                "source_id": "aihub_seedling_growth",
                "title": f"{crop} {stage} 육묘 생장단계 라벨 요약",
                "publisher": "AI Hub",
                "url": "https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71829",
                "license": "Dataset-specific approval and terms required",
                "collected_at": collected_at,
                "category": "crop_growth_stage",
                "priority": 2,
                "usage_scope": "rag_and_image_manifest",
                "crop_or_plant": [crop],
                "symptom_keywords": symptom_keywords,
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
                "crop_name": record.get("crop_name", ""),
                "growth_stage": record.get("growth_stage", ""),
                "shoot_location": record.get("shoot_location", ""),
                "shoot_view": record.get("shoot_view", ""),
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
        raise RuntimeError(f"No seedling label zip files found. Put files under {DEFAULT_INPUT_DIR} or pass --input.")

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
            "crop_name",
            "growth_stage",
            "shoot_location",
            "shoot_view",
            "storage_path",
            "notes",
        ],
    )
    print(f"Parsed {label_count} AI Hub seedling label records from {len(zip_paths)} zip files.")
    print(f"Wrote {doc_count} RAG summary documents to {args.docs_output}.")
    print(f"Wrote {manifest_count} image manifest rows to {args.image_manifest_output}.")


if __name__ == "__main__":
    main()
