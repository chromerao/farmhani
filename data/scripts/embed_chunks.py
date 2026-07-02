from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from common import read_jsonl, stable_hash, write_jsonl
from config import DEFAULT_CHUNKS, DEFAULT_EMBEDDED_CHUNKS, EMBEDDING_MODEL, OPENAI_API_KEY

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed RAG chunks for pgvector ingestion.")
    parser.add_argument("--input", default=str(DEFAULT_CHUNKS))
    parser.add_argument("--output", default=str(DEFAULT_EMBEDDED_CHUNKS))
    parser.add_argument("--mode", choices=["openai", "hash"], default="openai")
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    parser.add_argument("--dimensions", type=int, default=1536)
    parser.add_argument("--batch-size", type=int, default=50)
    return parser.parse_args()


def hash_embedding(text: str, dimensions: int) -> list[float]:
    values = []
    seed = stable_hash(text, 64)
    counter = 0
    while len(values) < dimensions:
        digest = stable_hash(f"{seed}:{counter}", 64)
        for i in range(0, len(digest), 4):
            if len(values) >= dimensions:
                break
            raw = int(digest[i : i + 4], 16)
            values.append((raw / 65535.0) * 2.0 - 1.0)
        counter += 1
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [round(value / norm, 8) for value in values]


def openai_embeddings(texts: list[str], model: str, dimensions: int) -> list[list[float]]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing. Set it in .env or use --mode hash for local smoke tests.")

    payload: dict[str, Any] = {"model": model, "input": texts}
    if model.startswith("text-embedding-3"):
        payload["dimensions"] = dimensions

    request = Request(
        OPENAI_EMBEDDINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))

    data = sorted(body["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in data]


def batched(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def main() -> None:
    args = parse_args()
    chunks = read_jsonl(Path(args.input))
    embedded: list[dict[str, Any]] = []

    for batch in batched(chunks, args.batch_size):
        texts = [row["text"] for row in batch]
        if args.mode == "hash":
            vectors = [hash_embedding(text, args.dimensions) for text in texts]
            embedding_model = f"local-hash-demo-{args.dimensions}"
        else:
            vectors = openai_embeddings(texts, args.model, args.dimensions)
            embedding_model = args.model

        for row, vector in zip(batch, vectors, strict=True):
            metadata = dict(row.get("metadata") or {})
            metadata["embeddingModel"] = embedding_model
            embedded.append({**row, "embedding": vector, "metadata": metadata})

    count = write_jsonl(Path(args.output), embedded)
    print(f"Wrote {count} embedded chunks: {args.output}")


if __name__ == "__main__":
    main()
