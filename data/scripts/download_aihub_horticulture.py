from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from common import CATALOG_DIR, DATA_DIR, ensure_dirs, load_env

CATALOG_PATH = CATALOG_DIR / "aihub_horticulture_files.json"
DEFAULT_OUTPUT_DIR = DATA_DIR / "external" / "aihub" / "horticulture"
AIHUB_VERSION = "0.6"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download selected AI Hub horticulture files by dataset/file key."
    )
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--dataset-key", default=None)
    parser.add_argument("--file-key", action="append", help="AI Hub fileSn. Repeatable.")
    parser.add_argument("--kind", choices=["label", "source_image", "all"], default="label")
    parser.add_argument("--max-priority", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-download even when the catalog filename already exists.")
    parser.add_argument("--keep-tar", action="store_true")
    return parser.parse_args()


def load_catalog(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_files(catalog: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    files = catalog.get("files", [])
    if args.file_key:
        wanted = set(args.file_key)
        return [file for file in files if str(file.get("file_key")) in wanted]
    rows = []
    for file in files:
        if args.kind != "all" and file.get("kind") != args.kind:
            continue
        if int(file.get("priority", 99)) > args.max_priority:
            continue
        rows.append(file)
    return rows


def safe_extract_tar(tar_path: Path, output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    with tarfile.open(tar_path) as tar:
        for member in tar.getmembers():
            target = (output_dir / member.name).resolve()
            if not str(target).startswith(str(output_dir)):
                raise RuntimeError(f"Unsafe tar member path: {member.name}")
        tar.extractall(output_dir)


def part_sort_key(path: Path) -> tuple[str, int]:
    match = re.search(r"\.part(\d+)$", path.name)
    return (re.sub(r"\.part\d+$", "", path.name), int(match.group(1)) if match else -1)


def merge_part_files(output_dir: Path) -> int:
    grouped: dict[Path, list[Path]] = {}
    for part in output_dir.rglob("*.part*"):
        if not re.search(r"\.part\d+$", part.name):
            continue
        target = part.with_name(re.sub(r"\.part\d+$", "", part.name))
        grouped.setdefault(target, []).append(part)

    merged = 0
    for target, parts in grouped.items():
        parts = sorted(parts, key=part_sort_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            for part in parts:
                with part.open("rb") as src:
                    shutil.copyfileobj(src, out)
        for part in parts:
            part.unlink()
        merged += 1
        print(f"Merged {len(parts)} parts -> {target}")
    return merged


def download_file(dataset_key: str, file_key: str, api_key: str, output_dir: Path, keep_tar: bool) -> None:
    url = f"https://api.aihub.or.kr/down/{AIHUB_VERSION}/{dataset_key}.do?fileSn={file_key}"
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(prefix=f"aihub_{dataset_key}_{file_key}_", suffix=".tar", delete=False) as tmp:
        tar_path = Path(tmp.name)

    request = Request(url, headers={"apikey": api_key})
    try:
        with urlopen(request, timeout=120) as response, tar_path.open("wb") as f:
            shutil.copyfileobj(response, f)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        tar_path.unlink(missing_ok=True)
        raise RuntimeError(f"AI Hub download failed for fileSn={file_key}: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        tar_path.unlink(missing_ok=True)
        raise RuntimeError(f"AI Hub download failed for fileSn={file_key}: {exc.reason}") from exc

    try:
        safe_extract_tar(tar_path, output_dir)
        merge_part_files(output_dir)
    finally:
        if keep_tar:
            kept = output_dir / f"download_{dataset_key}_{file_key}.tar"
            shutil.move(str(tar_path), kept)
            print(f"Kept tar: {kept}")
        else:
            tar_path.unlink(missing_ok=True)


def catalog_file_exists(output_dir: Path, file: dict[str, Any]) -> Path | None:
    filename = file.get("filename")
    if not filename:
        return None
    matches = list(output_dir.rglob(filename))
    return matches[0] if matches else None


def main() -> None:
    args = parse_args()
    ensure_dirs()
    catalog = load_catalog(Path(args.catalog))
    dataset_key = args.dataset_key or str(catalog["dataset_key"])
    output_dir = Path(args.output_dir)
    files = selected_files(catalog, args)

    if not files:
        raise RuntimeError("No AI Hub files matched the requested filters.")

    print(f"Dataset: {dataset_key}")
    print(f"Output: {output_dir}")
    print("Selected files:")
    for file in files:
        print(f"- {file['file_key']} {file.get('filename')} ({file.get('size')}, priority {file.get('priority')})")

    if args.dry_run:
        return

    env = load_env()
    api_key = env.get("AIHUB_API_KEY") or env.get("AIHUB_APIKEY") or ""
    if not api_key:
        raise RuntimeError("Missing AIHUB_API_KEY or AIHUB_APIKEY in environment/.env.")

    for file in files:
        existing = catalog_file_exists(output_dir, file)
        if existing and not args.force:
            print(f"Skipped existing file: {existing}")
            continue
        download_file(dataset_key, str(file["file_key"]), api_key, output_dir, args.keep_tar)


if __name__ == "__main__":
    main()
