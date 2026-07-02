from __future__ import annotations

import argparse
from pathlib import Path

from common import is_uuid, read_jsonl
from config import DEFAULT_CHUNKS, DEFAULT_EMBEDDED_CHUNKS, DEFAULT_SOURCES

REQUIRED_SOURCE_FIELDS = ["source_id", "title", "publisher", "url", "license", "category"]
REQUIRED_CHUNK_FIELDS = [
    "chunk_id",
    "source_id",
    "title",
    "publisher",
    "url",
    "license",
    "category",
    "symptom_keywords",
    "safety_tags",
    "section",
    "excerpt",
    "text",
]


def meaningful_text_score(text: str) -> float:
    compact = "".join(char for char in text if not char.isspace())
    if not compact:
        return 0.0
    meaningful = sum(1 for char in compact if char.isalpha() or "\uac00" <= char <= "\ud7a3")
    return meaningful / len(compact)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate processed RAG data before backend ingestion.")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES))
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS))
    parser.add_argument("--embedded", default=str(DEFAULT_EMBEDDED_CHUNKS))
    parser.add_argument("--allow-missing", action="store_true")
    return parser.parse_args()


def require_path(path: Path, allow_missing: bool) -> bool:
    if path.exists():
        return True
    if allow_missing:
        print(f"SKIP missing file: {path}")
        return False
    raise FileNotFoundError(path)


def validate_required(row: dict, fields: list[str], label: str, index: int) -> list[str]:
    errors = []
    for field in fields:
        if row.get(field) in (None, "", []):
            errors.append(f"{label}[{index}] missing {field}")
    return errors


def main() -> None:
    args = parse_args()
    errors: list[str] = []

    sources_path = Path(args.sources)
    chunks_path = Path(args.chunks)
    embedded_path = Path(args.embedded)

    sources = read_jsonl(sources_path) if require_path(sources_path, args.allow_missing) else []
    chunks = read_jsonl(chunks_path) if require_path(chunks_path, args.allow_missing) else []
    embedded = read_jsonl(embedded_path) if embedded_path.exists() else []

    source_ids = {source.get("source_id") for source in sources}

    for index, source in enumerate(sources, start=1):
        errors.extend(validate_required(source, REQUIRED_SOURCE_FIELDS, "source", index))
        if source.get("source_id") and not is_uuid(source["source_id"]):
            errors.append(f"source[{index}] source_id must be UUID: {source.get('source_id')}")

    seen_chunk_ids: set[str] = set()
    for index, chunk in enumerate(chunks, start=1):
        errors.extend(validate_required(chunk, REQUIRED_CHUNK_FIELDS, "chunk", index))
        chunk_id = chunk.get("chunk_id")
        if chunk_id and not is_uuid(chunk_id):
            errors.append(f"chunk[{index}] chunk_id must be UUID: {chunk_id}")
        if chunk.get("source_id") and not is_uuid(chunk["source_id"]):
            errors.append(f"chunk[{index}] source_id must be UUID: {chunk.get('source_id')}")
        if chunk_id in seen_chunk_ids:
            errors.append(f"chunk[{index}] duplicate chunk_id {chunk_id}")
        seen_chunk_ids.add(chunk_id)
        if source_ids and chunk.get("source_id") not in source_ids:
            errors.append(f"chunk[{index}] source_id not found in sources: {chunk.get('source_id')}")
        if "pesticide" in str(chunk.get("category")) and "pesticide_caution" not in chunk.get("safety_tags", []):
            errors.append(f"chunk[{index}] pesticide category requires pesticide_caution")
        if not isinstance(chunk.get("symptom_keywords"), list):
            errors.append(f"chunk[{index}] symptom_keywords must be a list")
        text = str(chunk.get("text") or "")
        excerpt = str(chunk.get("excerpt") or "")
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        if len(text) < 80:
            errors.append(f"chunk[{index}] text is too short for RAG citation display")
        if meaningful_text_score(text) < 0.45:
            errors.append(f"chunk[{index}] text looks non-document-like or mostly numeric/symbolic")
        if excerpt and excerpt not in text and text[:80] not in excerpt:
            errors.append(f"chunk[{index}] excerpt should be derived from chunk text")
        if metadata:
            for field in ["section", "excerpt", "contentPreview"]:
                if not metadata.get(field):
                    errors.append(f"chunk[{index}] metadata missing {field}")

    for index, chunk in enumerate(embedded, start=1):
        vector = chunk.get("embedding")
        if not isinstance(vector, list) or len(vector) != 1536:
            errors.append(f"embedded[{index}] embedding must be a 1536-value list")

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Validation passed.")
    print(f"Sources: {len(sources)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Embedded chunks: {len(embedded)}")


if __name__ == "__main__":
    main()
