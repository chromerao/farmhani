from __future__ import annotations

from pathlib import Path

from common import (
    CATALOG_DIR,
    DATA_DIR,
    INTERIM_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    REPO_ROOT,
    VECTORSTORE_DIR,
    load_env,
)

ENV = load_env()

OPENAI_API_KEY = ENV.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = ENV.get("EMBEDDING_MODEL", "text-embedding-3-small")

SUPABASE_URL = ENV.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = ENV.get("SUPABASE_ANON_KEY", "")

NONGSARO_API_KEY = ENV.get("NONGSARO_API_KEY", "")
NCPMS_API_KEY = ENV.get("NCPMS_API_KEY", "")
PSIS_API_KEY = ENV.get("PSIS_API_KEY", "")
AIHUB_API_KEY = ENV.get("AIHUB_API_KEY", "") or ENV.get("AIHUB_APIKEY", "")
WEATHER_API_KEY = ENV.get("WEATHER_API_KEY", "")
PUBLIC_DATA_PORTAL_API_KEY = ENV.get("PUBLIC_DATA_PORTAL_API_KEY", "")

DEFAULT_NORMALIZED_DOCS = INTERIM_DIR / "rag_documents.normalized.jsonl"
DEFAULT_CHUNKS = PROCESSED_DIR / "rag_chunks.sample.jsonl"
DEFAULT_SOURCES = PROCESSED_DIR / "rag_sources.sample.jsonl"
DEFAULT_EMBEDDED_CHUNKS = VECTORSTORE_DIR / "rag_chunks.embedded.jsonl"


def require_env(name: str) -> str:
    value = ENV.get(name, "")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def path_from_repo(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path
