from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import CATALOG_DIR, PROCESSED_DIR, load_source_registry, merge_safety_tags, read_jsonl, slugify, today, write_jsonl

REQUIRED_FIELDS = ["name_ko", "source_id", "source_url", "license"]
DEFAULT_INPUT = CATALOG_DIR / "priority_plant_catalog.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize reviewed plant/crop records into plant_master.sample.jsonl.")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Manual/reviewed plant records JSONL. Raw crawling should be reviewed before this step.",
    )
    parser.add_argument("--output", default=str(PROCESSED_DIR / "plant_master.sample.jsonl"))
    return parser.parse_args()


def normalize_record(row: dict[str, Any], registry: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
    if missing:
        raise ValueError(f"Plant record missing required fields {missing}: {row}")

    source = registry.get(row["source_id"], {})
    name_ko = row["name_ko"]
    plant_id = row.get("plant_id") or slugify(row.get("name_scientific") or name_ko, "plant")

    return {
        "plant_id": plant_id,
        "name_ko": name_ko,
        "name_scientific": row.get("name_scientific", ""),
        "name_en": row.get("name_en", ""),
        "aliases": row.get("aliases", []),
        "family": row.get("family", ""),
        "category": row.get("category") or [source.get("category", "uncategorized")],
        "description": row.get("description", ""),
        "light_requirement": row.get("light_requirement", ""),
        "water_requirement": row.get("water_requirement", ""),
        "min_winter_temp_c": row.get("min_winter_temp_c"),
        "growth_form": row.get("growth_form", ""),
        "leaf_color": row.get("leaf_color", []),
        "source_id": row["source_id"],
        "source_url": row["source_url"],
        "license": row["license"],
        "collected_at": row.get("collected_at") or today(),
        "safety_tags": merge_safety_tags(row.get("safety_tags")),
    }


def main() -> None:
    args = parse_args()
    registry = load_source_registry()
    records = [normalize_record(row, registry) for row in read_jsonl(Path(args.input))]
    count = write_jsonl(Path(args.output), records)
    print(f"Wrote {count} plant master records: {args.output}")


if __name__ == "__main__":
    main()
