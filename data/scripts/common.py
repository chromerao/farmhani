from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import unicodedata
import uuid
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CATALOG_DIR = DATA_DIR / "catalog"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
VECTORSTORE_DIR = DATA_DIR / "vectorstore"

DEFAULT_HEADERS = {
    "User-Agent": "FarmhaniDataPipeline/0.1 (+https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN30-3rd-3Team)"
}
SOURCE_UUID_NAMESPACE = uuid.UUID("4a8ecf91-111c-4f56-a965-f3f3f0d9d9b1")
CHUNK_UUID_NAMESPACE = uuid.UUID("70d3a994-55e0-4e58-8477-f128e1cbf65f")

KNOWN_CROP_OR_PLANT_NAMES = [
    "몬스테라",
    "스파티필럼",
    "호접란",
    "금전수",
    "스투키",
    "선인장",
    "테이블야자",
    "홍콩야자",
    "보스턴고사리",
    "관음죽",
    "벵갈고무나무",
    "디펜바키아",
    "올리브나무",
    "오렌지쟈스민",
    "인도고무나무",
    "스킨답서스",
    "필로덴드론",
    "알로카시아",
    "칼라데아",
    "마란타",
    "아레카야자",
    "드라세나",
    "행운목",
    "구문초",
    "구즈마니아",
    "공작야자",
    "개운죽",
    "가울테리아",
    "골드크레스트",
    "토마토",
    "고추",
    "상추",
    "배추",
    "양배추",
    "파프리카",
    "감자",
    "고구마",
    "오이",
    "딸기",
    "방울토마토",
    "가지",
    "호박",
    "수박",
    "참외",
    "무",
    "당근",
    "양파",
    "마늘",
    "대파",
    "부추",
    "깻잎",
    "콩",
    "완두",
    "복숭아",
    "옥수수",
    "벼",
    "난",
    "로즈마리",
    "바질",
    "민트",
    "라벤더",
    "장미",
    "벚나무",
    "벚꽃",
    "개나리",
    "해바라기",
    "국화",
    "튤립",
    "백합",
    "수국",
    "카네이션",
    "제라늄",
    "베고니아",
    "코스모스",
    "무궁화",
]

WEB_BOILERPLATE_PHRASES = [
    "본문 바로가기",
    "주메뉴 바로가기",
    "이 누리집은 대한민국 공식 전자정부 누리집입니다.",
    "화면크기",
    "작게 보통 조금 크게 크게 가장크게 초기화",
    "농업자재 영농기술 농업경영 연구정보 생활농업 농(農)영상 농사로소식 농업정보토탈서비스 농사로 활용가이드 농업자재",
    "통합검색",
    "내용삭제",
    "검색 첫단어 중간단어 끝단어",
    "첫단어 중간단어 끝단어",
    "전체메뉴",
    "전체메뉴 닫기",
    "홈 인쇄 공유",
    "X로 공유하기",
    "페이스북으로 공유하기",
    "카카오톡으로 공유하기",
    "밴드로 공유하기",
    "블로그로 공유하기",
    "URL 복사",
    "PDF 다운",
    "작성자 비밀번호 의견제시 등록",
    "이 페이지에서 제공하는 정보에 대해 만족하십니까?",
    "등록하기",
]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "div", "section", "article", "li", "br", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(UTC).date().isoformat()


def ensure_dirs() -> None:
    for directory in [RAW_DIR, INTERIM_DIR, PROCESSED_DIR, VECTORSTORE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_env() -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    for path in [REPO_ROOT / ".env", DATA_DIR / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return env


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSONL: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
            count += 1
    return count


def normalize_text(value: str) -> str:
    value = html.unescape(value)
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</(?:p|div|li|tr|h[1-6])>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n", value)
    return value.strip()


def html_to_text(raw_html: str) -> str:
    parser = TextExtractor()
    parser.feed(raw_html)
    return parser.text()


def clean_scraped_text(text: str, source_key: str | None = None, title: str | None = None) -> str:
    text = normalize_text(text)
    text = re.sub(r"\bhttps?://\S+", " ", text)
    text = re.sub(r"(?:병원체|곤충|해충|병피해|피해|상담)\s*사진\s*:\s*image\s*:", " ", text)
    text = re.sub(r"\bimage\s*:", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[ᄀ-ᄒ](?:\s+[ᄀ-ᄒ]){5,}", " ", text)
    text = re.sub(r"\bA\s+B\s+C\s+D\s+E\s+F\s+G\s+H\s+I\s+J\s+K\s+L\s+M\s+N\s+O\s+P\s+Q\s+R\s+S\s+T\s+U\s+V\s+W\s+X\s+Y\s+Z\b", " ", text)
    for phrase in WEB_BOILERPLATE_PHRASES:
        flexible_phrase = r"\s+".join(re.escape(part) for part in phrase.split())
        text = re.sub(flexible_phrase, " ", text)
        text = text.replace(phrase, " ")
    text = re.sub(r"이전글\s+.*?\s+다음글\s+.*?\s+목록", " ", text)
    for footer_marker in ["농촌진흥청 농업전문정보", "대표전화 063-238-1000", "저작권정책"]:
        if footer_marker in text:
            text = text[: text.find(footer_marker)]
    text = re.sub(r"\b농사로\s+농사로\b", "농사로", text)
    text = re.sub(r"(?:\b닫기\b\s*){2,}", " ", text)

    source_key = source_key or ""
    if source_key.startswith("nongsaro"):
        markers = [
            "실내정원용 식물 검색 상세표",
            "학명 :",
            "물주기",
            "작물검색",
            "생산기술",
            "주요핵심기술",
        ]
        candidates = [text]
        if title:
            title_tail = title.split(" - ")[-1].strip()
            if title_tail and title_tail in text:
                candidates.append(text[text.find(title_tail) :])
        for marker in markers:
            if marker in text:
                candidates.append(text[text.find(marker) :])
        text = min(candidates, key=len)

    return normalize_text(text)


def infer_crop_or_plant(*values: Any) -> list[str]:
    haystack = normalize_text(" ".join(str(value) for value in values if value))
    found: list[str] = []
    for name in KNOWN_CROP_OR_PLANT_NAMES:
        if name in haystack and name not in found:
            found.append(name)
    return found


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def uuid_for_source_key(source_key: str) -> str:
    return str(uuid.uuid5(SOURCE_UUID_NAMESPACE, source_key))


def uuid_for_chunk_key(chunk_key: str) -> str:
    return str(uuid.uuid5(CHUNK_UUID_NAMESPACE, chunk_key))


def is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def slugify(value: str, fallback_prefix: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    if not slug:
        slug = f"{fallback_prefix}_{stable_hash(value, 10)}"
    return slug


def http_get_text(url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> str:
    full_url = url
    if params:
        full_url = f"{url}?{urlencode({k: v for k, v in params.items() if v is not None})}"
    request = Request(full_url, headers=DEFAULT_HEADERS)
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"GET {full_url} failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"GET {full_url} failed: {exc.reason}") from exc


def chunk_text(text: str, max_chars: int = 2200, overlap_chars: int = 250) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            sentence_end = max(text.rfind(".", start, end), text.rfind("\n", start, end))
            if sentence_end > start + int(max_chars * 0.45):
                end = sentence_end + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return [chunk for chunk in chunks if chunk]


def load_source_registry() -> dict[str, dict[str, Any]]:
    registry = read_json(CATALOG_DIR / "source_registry.json")
    sources = {}
    for source in registry["sources"]:
        source_key = source.get("source_key") or source["source_id"]
        source_uuid = source.get("source_uuid") or uuid_for_source_key(source_key)
        enriched = {
            **source,
            "source_key": source_key,
            "source_uuid": source_uuid,
        }
        sources[source_key] = enriched
        sources[source_uuid] = enriched
    return sources


def load_taxonomy() -> dict[str, Any]:
    return read_json(CATALOG_DIR / "category_taxonomy.json")


def merge_safety_tags(*tag_lists: Iterable[str] | None) -> list[str]:
    tags: list[str] = []
    for tag_list in tag_lists:
        if not tag_list:
            continue
        for tag in tag_list:
            if tag and tag not in tags:
                tags.append(tag)
    if "not_diagnosis" not in tags:
        tags.insert(0, "not_diagnosis")
    return tags


def detect_symptom_keywords(text: str) -> list[str]:
    taxonomy = load_taxonomy()
    matched: list[str] = []
    lowered = text.lower()
    for group, keywords in taxonomy.get("symptom_keywords", {}).items():
        if any(keyword.lower() in lowered for keyword in keywords):
            matched.append(group)
    return matched
