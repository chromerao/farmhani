from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from common import (
    INTERIM_DIR,
    RAW_DIR,
    clean_scraped_text,
    detect_symptom_keywords,
    ensure_dirs,
    html_to_text,
    http_get_text,
    infer_crop_or_plant,
    load_source_registry,
    merge_safety_tags,
    now_iso,
    stable_hash,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch public web sources and convert HTML pages to normalized document candidates."
    )
    parser.add_argument(
        "--source-id",
        action="append",
        help="Source id from data/catalog/source_registry.json. Repeatable. Defaults to all web sources.",
    )
    parser.add_argument(
        "--output",
        default=str(INTERIM_DIR / "web_documents.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument("--max-priority", type=int, default=3, help="Default limits collection to MVP priorities.")
    parser.add_argument("--all", action="store_true", help="Collect all registry web/catalog sources.")
    parser.add_argument(
        "--max-detail-pages",
        type=int,
        default=12,
        help="Maximum Nongsaro detail pages to fetch per source. Use 0 to disable.",
    )
    parser.add_argument("--no-details", action="store_true", help="Only collect top-level registry URLs.")
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def should_collect(source: dict[str, Any], selected_ids: set[str] | None, max_priority: int, collect_all: bool) -> bool:
    if selected_ids and source["source_id"] not in selected_ids:
        return False
    if not selected_ids and not collect_all and int(source.get("priority", 99)) > max_priority:
        return False
    return source.get("collection_mode") in {
        "web",
        "web_or_api",
        "web_or_api_later",
        "pdf_manifest_or_web",
        "catalog_only",
    }


def make_doc(source: dict[str, Any], url: str, raw_html: str, raw_path: Path, title: str | None = None) -> dict[str, Any]:
    source_id = source["source_id"]
    doc_title = title or source["title"]
    source_key = source["source_key"]
    text = clean_scraped_text(html_to_text(raw_html), source_key=source_key, title=doc_title)
    crop_or_plant = list(source.get("target_crops", []))
    is_index_doc = source_key.startswith("nongsaro") and doc_title == source["title"]
    if not is_index_doc:
        inference_text = doc_title if source_key.startswith("nongsaro") else f"{doc_title} {text}"
        inferred = infer_crop_or_plant(inference_text)
        for name in inferred:
            if name not in crop_or_plant:
                crop_or_plant.append(name)

    return {
        "doc_id": f"{source_id}:{stable_hash(url)}",
        "source_key": source_key,
        "source_id": source["source_uuid"],
        "title": doc_title,
        "publisher": source["publisher"],
        "url": url,
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": source.get("usage_scope", "rag"),
        "safety_tags": merge_safety_tags(source.get("safety_tags")),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": crop_or_plant,
        "raw_path": str(raw_path),
        "collected_at": now_iso(),
        "text": text,
    }


def write_raw_html(source_id: str, url: str, raw_html: str) -> Path:
    raw_dir = RAW_DIR / source_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{stable_hash(url)}.html"
    raw_path.write_text(raw_html, encoding="utf-8", newline="\n")
    return raw_path


def collect_source(source: dict[str, Any], timeout: int) -> dict[str, Any]:
    source_id = source["source_id"]
    url = source["url"]
    raw_html = http_get_text(url, timeout=timeout)
    raw_path = write_raw_html(source_id, url, raw_html)
    return make_doc(source, url, raw_html, raw_path)


def attr_value(tag: str, name: str) -> str:
    match = re.search(rf'{name}\s*=\s*([\'"])(.*?)\1', tag, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return html.unescape(match.group(2)).strip()


def absolutize(base_url: str, candidate: str) -> str:
    candidate = html.unescape(candidate).strip()
    if not candidate or candidate.startswith(("javascript:", "#", "mailto:", "tel:")):
        return ""
    return urljoin(base_url, candidate)


def nongsaro_title_for_url(raw_html: str, url: str) -> str:
    parsed = urlparse(url)
    cntnts_no = ""
    if "cntntsNo=" in parsed.query:
        match = re.search(r"(?:^|&)cntntsNo=([^&]+)", parsed.query)
        cntnts_no = match.group(1) if match else ""
    if cntnts_no:
        pattern = rf"fncContentSub\('{re.escape(cntnts_no)}'\).*?<img[^>]+alt=(['\"])(.*?)\1"
        match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return html.unescape(match.group(2)).strip()

    for tag in re.findall(r"<a\b[^>]*>", raw_html, flags=re.IGNORECASE | re.DOTALL):
        href = attr_value(tag, "href")
        onclick = attr_value(tag, "onclick")
        title = attr_value(tag, "title")
        if href and href in url and title:
            return title
        if onclick and title and href in {"#link", "#"}:
            location_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
            if location_match and absolutize("https://www.nongsaro.go.kr", location_match.group(1)) == url:
                return title
    return ""


def extract_nongsaro_detail_links(source: dict[str, Any], raw_html: str) -> list[dict[str, str]]:
    base_url = source["url"]
    source_id = source["source_id"]
    links: dict[str, str] = {}

    if source_id == "nongsaro_indoor_catalog":
        for cntnts_no in re.findall(r"fncContentSub\('(\d+)'\)", raw_html):
            url = f"https://www.nongsaro.go.kr/portal/ps/psz/psza/contentSub.ps?menuId=PS00376&cntntsNo={cntnts_no}"
            links.setdefault(url, nongsaro_title_for_url(raw_html, url))

    for tag in re.findall(r"<a\b[^>]*>", raw_html, flags=re.IGNORECASE | re.DOTALL):
        title = attr_value(tag, "title")
        for candidate in [attr_value(tag, "href")]:
            url = absolutize(base_url, candidate)
            if is_relevant_nongsaro_detail(source_id, url):
                links.setdefault(url, title or nongsaro_title_for_url(raw_html, url))

        onclick = attr_value(tag, "onclick")
        for candidate in re.findall(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick):
            url = absolutize(base_url, candidate)
            if is_relevant_nongsaro_detail(source_id, url):
                links.setdefault(url, title or nongsaro_title_for_url(raw_html, url))

    return [{"url": url, "title": title} for url, title in links.items()]


def is_relevant_nongsaro_detail(source_id: str, url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.netloc and "nongsaro.go.kr" not in parsed.netloc:
        return False
    if source_id == "nongsaro_indoor_catalog":
        return "/portal/ps/psz/psza/contentSub.ps" in parsed.path and "cntntsNo=" in parsed.query
    if source_id == "nongsaro_crop_tech":
        return (
            "/portal/ps/psv/psvr/psvre/curationDtl.ps" in parsed.path
            or "/portal/ps/psz/psza/contentNsSub.ps" in parsed.path
            or ("/portal/farmTechMain.ps" in parsed.path and "stdPrdlstCode=" in parsed.query)
        )
    return False


def collect_detail_docs(
    source: dict[str, Any],
    root_raw_html: str,
    timeout: int,
    max_detail_pages: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if max_detail_pages <= 0 or source["source_id"] not in {"nongsaro_indoor_catalog", "nongsaro_crop_tech"}:
        return [], []

    links = extract_nongsaro_detail_links(source, root_raw_html)[:max_detail_pages]
    docs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for link in links:
        url = link["url"]
        try:
            raw_html = http_get_text(url, timeout=timeout)
            raw_path = write_raw_html(source["source_id"], url, raw_html)
            title = link.get("title") or nongsaro_title_for_url(root_raw_html, url) or source["title"]
            docs.append(make_doc(source, url, raw_html, raw_path, title=f"{source['title']} - {title}"))
        except Exception as exc:
            errors.append({"source_id": source["source_id"], "url": url, "error": str(exc)})
    return docs, errors


def main() -> None:
    args = parse_args()
    ensure_dirs()
    registry = load_source_registry()
    selected_ids = set(args.source_id) if args.source_id else None

    docs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    seen_source_keys: set[str] = set()
    for source in registry.values():
        if source["source_key"] in seen_source_keys:
            continue
        seen_source_keys.add(source["source_key"])
        if not should_collect(source, selected_ids, args.max_priority, args.all):
            continue
        try:
            root_doc = collect_source(source, timeout=args.timeout)
            detail_docs: list[dict[str, Any]] = []
            detail_errors: list[dict[str, str]] = []
            if not args.no_details:
                detail_docs, detail_errors = collect_detail_docs(
                    source=source,
                    root_raw_html=Path(root_doc["raw_path"]).read_text(encoding="utf-8", errors="replace"),
                    timeout=args.timeout,
                    max_detail_pages=args.max_detail_pages,
                )
                errors.extend(detail_errors)
            if detail_docs and source["source_id"] in {"nongsaro_indoor_catalog", "nongsaro_crop_tech"}:
                docs.extend(detail_docs)
            else:
                docs.append(root_doc)
        except Exception as exc:
            errors.append({"source_id": source["source_id"], "error": str(exc)})

    output = Path(args.output)
    count = write_jsonl(output, docs)
    if errors:
        error_output = output.with_suffix(".errors.jsonl")
        write_jsonl(error_output, errors)
        print(f"Collected {count} documents with {len(errors)} errors. Errors: {error_output}")
    else:
        stale_error_output = output.with_suffix(".errors.jsonl")
        if stale_error_output.exists():
            stale_error_output.unlink()
        print(f"Collected {count} documents: {output}")


if __name__ == "__main__":
    main()
