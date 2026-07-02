from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from common import (
    INTERIM_DIR,
    RAW_DIR,
    detect_symptom_keywords,
    ensure_dirs,
    http_get_text,
    load_source_registry,
    merge_safety_tags,
    normalize_text,
    now_iso,
    stable_hash,
    write_jsonl,
)
from config import PSIS_API_KEY


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect PSIS pesticide safety records. This is safety-reference-only data."
    )
    parser.add_argument("--crop", help="Crop name, e.g. 토마토")
    parser.add_argument("--pest", help="Disease, pest, or weed name filter.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--service-code", default="SVC01", help="PSIS list service defaults to SVC01.")
    parser.add_argument("--service-type", default="AA002", help="PSIS response type option from guide page.")
    parser.add_argument("--output", default=str(INTERIM_DIR / "psis_pesticide_safety.jsonl"))
    parser.add_argument("--allow-missing-key", action="store_true")
    return parser.parse_args()


def parse_response(raw: str) -> list[dict[str, Any]]:
    raw = raw.strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [row for row in parsed if isinstance(row, dict)]
        if isinstance(parsed, dict):
            for key in ["data", "items", "list", "body"]:
                value = parsed.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
            return [parsed]
    except json.JSONDecodeError:
        pass

    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return [{"raw_text": raw}]

    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        row = {child.tag: normalize_text(child.text or "") for child in list(item)}
        if row:
            rows.append(row)
    if rows:
        return rows

    return [{root.tag: normalize_text(" ".join(root.itertext()))}]


def row_to_document(row: dict[str, Any], source: dict[str, Any], crop: str | None, pest: str | None) -> dict[str, Any]:
    text_parts = []
    for key, value in row.items():
        if value in (None, ""):
            continue
        text_parts.append(f"{key}: {value}")
    text = normalize_text("\n".join(text_parts))
    filters = [value for value in [crop, pest] if value]
    title_suffix = " / ".join(filters) if filters else "검색 결과"

    return {
        "doc_id": f"{source['source_id']}:{stable_hash(text or title_suffix)}",
        "source_key": source["source_key"],
        "source_id": source["source_uuid"],
        "title": f"{source['title']} - {title_suffix}",
        "publisher": source["publisher"],
        "url": source["url"],
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": "safety_reference_only",
        "safety_tags": merge_safety_tags(source.get("safety_tags"), ["pesticide_caution"]),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": [value for value in [crop] if value],
        "collected_at": now_iso(),
        "raw_record": row,
        "text": text,
    }


def main() -> None:
    args = parse_args()
    ensure_dirs()
    source = load_source_registry()["psis_pesticide_safety"]

    if not PSIS_API_KEY:
        message = (
            "PSIS_API_KEY is missing. Request an API key from the PSIS OpenAPI guide, "
            "then set PSIS_API_KEY in .env. No pesticide safety data was collected."
        )
        if args.allow_missing_key:
            print(message)
            write_jsonl(Path(args.output), [])
            return
        raise RuntimeError(message)

    params = {
        "apiKey": PSIS_API_KEY,
        "serviceCode": args.service_code,
        "serviceType": args.service_type,
        "displayCount": min(args.limit, 100),
        "startPoint": 1,
    }
    if args.crop:
        params["cropName"] = args.crop
    if args.pest:
        params["diseaseWeedName"] = args.pest

    raw = http_get_text(source["api_url"], params=params, timeout=30)
    raw_dir = RAW_DIR / source["source_id"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{stable_hash(json.dumps(params, ensure_ascii=False, sort_keys=True))}.txt"
    raw_path.write_text(raw, encoding="utf-8", newline="\n")

    rows = parse_response(raw)[: args.limit]
    docs = [row_to_document(row, source, args.crop, args.pest) for row in rows]
    count = write_jsonl(Path(args.output), docs)
    print(f"Collected {count} PSIS safety documents: {args.output}")


if __name__ == "__main__":
    main()
