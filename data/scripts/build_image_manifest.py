from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from common import PROCESSED_DIR, load_source_registry, read_jsonl, write_csv

FIELDNAMES = [
    "image_id",
    "storage_path",
    "plant_name",
    "label",
    "status",
    "source_id",
    "source_url",
    "license",
    "usage_scope",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build image_manifest.sample.csv from reviewed image metadata. Does not store image files."
    )
    parser.add_argument(
        "--input",
        help=(
            "Optional JSONL rows with image_id, storage_path, plant_name, label, status, notes. "
            "If omitted, an empty manifest with header is created."
        ),
    )
    parser.add_argument("--source-id", default="aihub_agriculture_datasets")
    parser.add_argument("--output", default=str(PROCESSED_DIR / "image_manifest.sample.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = load_source_registry()[args.source_id]
    rows: list[dict[str, Any]] = []
    if args.input:
        rows = read_jsonl(Path(args.input))

    manifest_rows = []
    for index, row in enumerate(rows, start=1):
        manifest_rows.append(
            {
                "image_id": row.get("image_id") or f"{args.source_id}_{index:06d}",
                "storage_path": row.get("storage_path", ""),
                "plant_name": row.get("plant_name", ""),
                "label": row.get("label", ""),
                "status": row.get("status", "reference_only"),
                "source_id": args.source_id,
                "source_url": row.get("source_url") or source["url"],
                "license": row.get("license") or source["license"],
                "usage_scope": row.get("usage_scope") or source["usage_scope"],
                "notes": row.get("notes") or "Original image file must not be committed to Git.",
            }
        )

    count = write_csv(Path(args.output), manifest_rows, FIELDNAMES)
    print(f"Wrote {count} image manifest rows: {args.output}")


if __name__ == "__main__":
    main()
