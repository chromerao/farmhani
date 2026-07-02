from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import PROCESSED_DIR, read_jsonl

DEFAULT_PLANTS = PROCESSED_DIR / "plant_master.sample.jsonl"
DEFAULT_CHUNKS = PROCESSED_DIR / "rag_chunks.sample.jsonl"

CARE_CATEGORIES = {"indoor_care", "crop_care", "ornamental_care", "herb"}
WEAK_REFERENCE_SOURCES = {"ncpms_pest_reference", "ncpms_openapi_guide", "aihub_horticulture_watering_growth", "aihub_seedling_growth"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check plant catalog coverage against RAG care documents.")
    parser.add_argument("--plants", default=str(DEFAULT_PLANTS))
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS))
    parser.add_argument("--min-care-chunks", type=int, default=1)
    parser.add_argument("--fail-on-missing", action="store_true")
    return parser.parse_args()


def names_for(row: dict[str, Any]) -> list[str]:
    names = [row.get("name_ko"), row.get("name_scientific"), row.get("name_en")]
    names.extend(row.get("aliases") or [])
    return [str(name).strip() for name in names if str(name or "").strip()]


def is_care_chunk(chunk: dict[str, Any]) -> bool:
    category = str(chunk.get("category") or "")
    source_key = str(chunk.get("source_key") or "")
    if category not in CARE_CATEGORIES:
        return False
    return source_key not in WEAK_REFERENCE_SOURCES


def matching_chunks(plant: dict[str, Any], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = names_for(plant)
    matches = []
    for chunk in chunks:
        haystack = " ".join(
            [
                str(chunk.get("title") or ""),
                str(chunk.get("text") or ""),
                " ".join(str(item) for item in (chunk.get("crop_or_plant") or [])),
            ]
        )
        if any(name and name in haystack for name in names):
            matches.append(chunk)
    return matches


def main() -> None:
    args = parse_args()
    plants = read_jsonl(Path(args.plants))
    chunks = read_jsonl(Path(args.chunks))

    missing = []
    weak_only = []
    covered = []

    for plant in plants:
        matches = matching_chunks(plant, chunks)
        care_matches = [chunk for chunk in matches if is_care_chunk(chunk)]
        if len(care_matches) >= args.min_care_chunks:
            covered.append((plant, len(care_matches), len(matches)))
        elif matches:
            weak_only.append((plant, len(care_matches), len(matches)))
        else:
            missing.append(plant)

    print(f"Plant catalog records: {len(plants)}")
    print(f"Covered by care docs: {len(covered)}")
    print(f"Only weak/reference matches: {len(weak_only)}")
    print(f"No RAG matches: {len(missing)}")

    if weak_only:
        print("\nWeak/reference-only examples:")
        for plant, care_count, total_count in weak_only[:20]:
            print(f"- {plant.get('name_ko')} care={care_count} total={total_count}")

    if missing:
        print("\nMissing examples:")
        for plant in missing[:20]:
            print(f"- {plant.get('name_ko')}")

    if args.fail_on_missing and (missing or weak_only):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
