from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from common import (
    INTERIM_DIR,
    RAW_DIR,
    detect_symptom_keywords,
    ensure_dirs,
    html_to_text,
    http_get_text,
    load_source_registry,
    merge_safety_tags,
    normalize_text,
    now_iso,
    read_jsonl,
    stable_hash,
    write_jsonl,
)
from config import NCPMS_API_KEY


DEFAULT_ENDPOINT_URL = "http://ncpms.rda.go.kr/npmsAPI/service"

DISEASE_DETAIL_KEYS = {
    "cropName",
    "sickNameKor",
    "sickNameChn",
    "sickNameEng",
    "infectionRoute",
    "developmentCondition",
    "symptoms",
    "preventionMethod",
    "biologyPrvnbeMth",
    "chemicalPrvnbeMth",
    "etc",
    "virusName",
    "sfeNm",
    "virusImgList",
    "imageList",
}

INSECT_DETAIL_KEYS = {
    "insectOrder",
    "insectGenus",
    "insectFamily",
    "insectSpecies",
    "insectSpeciesKor",
    "distrbInfo",
    "stleInfo",
    "qrantInfo",
    "spcsPhotoData",
    "ecologyInfo",
    "damageInfo",
    "preventMethod",
    "insectLink",
    "enemyInsectSpeciesKor",
}

CONSULT_DETAIL_KEYS = {
    "dgnssReqSj",
    "dgnssReqNo",
    "registDatetm",
    "realm",
    "sidoName",
    "sigunguName",
    "emdName",
    "occrrncDatetm",
    "priyClName",
    "reqestCn",
    "answerDatetm",
    "answerSe",
    "answrrName",
    "dbyhs",
    "dgnssOpin",
    "prvnbeMth",
}

GENERIC_RECORD_KEYS = {
    "crop",
    "crop_name",
    "cropName",
    "pest_name",
    "disease_name",
    "insectKorName",
    "dgnssReqSj",
    "korName",
    "oprName",
    "divName",
    "sickNameKor",
    "symptom",
    "symptoms",
    "description",
}

PESTICIDE_WORDS = [
    "농약",
    "약제",
    "방제",
    "살균제",
    "살충제",
    "chemical",
    "pesticide",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect NCPMS pest/disease reference documents. "
            "SVC05 disease detail can be collected with --sick-key."
        )
    )
    parser.add_argument("--crop", help="Crop filter used for metadata, e.g. 토마토")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--manual-jsonl", help="Manual NCPMS records JSONL to normalize.")
    parser.add_argument("--endpoint-url", help="NCPMS API endpoint URL. Defaults to the public service URL.")
    parser.add_argument("--service-code", help="NCPMS serviceCode, e.g. SVC05 for disease detail.")
    parser.add_argument("--service-type", help="NCPMS serviceType, e.g. AA003 for JSON when the API supports it.")
    parser.add_argument("--sick-name-kor", help="Disease Korean name search term for SVC01.")
    parser.add_argument("--insect-kor-name", help="Insect Korean name search term for SVC03.")
    parser.add_argument("--dgnss-req-sj", help="Consultation title search term for SVC41.")
    parser.add_argument("--search-name", help="Integrated searchName for SVC16.")
    parser.add_argument("--div-code", help="Integrated SVC16 pest/disease/weed division code.")
    parser.add_argument("--crop-code", help="Integrated SVC16 cropCode.")
    parser.add_argument("--kor-name", help="Integrated SVC16 Korean name.")
    parser.add_argument("--opr-name", help="Integrated SVC16 English/scientific name.")
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="When using SVC01/SVC03/SVC41 search, fetch SVC05/SVC07/SVC42 details for discovered keys.",
    )
    parser.add_argument(
        "--sick-key",
        action="append",
        default=[],
        help="NCPMS SVC05 sickKey. Repeatable or comma-separated.",
    )
    parser.add_argument(
        "--insect-key",
        action="append",
        default=[],
        help="NCPMS SVC07 insectKey. Repeatable or comma-separated.",
    )
    parser.add_argument(
        "--dgnss-req-no",
        action="append",
        default=[],
        help="NCPMS SVC42 dgnssReqNo. Repeatable or comma-separated.",
    )
    parser.add_argument(
        "--sick-keys-file",
        help="Text/JSONL file containing sickKey values. One key per line, or JSONL rows with sickKey.",
    )
    parser.add_argument(
        "--insect-keys-file",
        help="Text/JSONL file containing insectKey values. One key per line, or JSONL rows with insectKey.",
    )
    parser.add_argument(
        "--dgnss-req-nos-file",
        help="Text/JSONL file containing dgnssReqNo values. One key per line, or JSONL rows with dgnssReqNo.",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Extra API query parameter as key=value. Repeatable.",
    )
    parser.add_argument(
        "--skip-guide",
        action="store_true",
        help="Skip collecting the public NCPMS OpenAPI guide page.",
    )
    parser.add_argument("--output", default=str(INTERIM_DIR / "ncpms_pest_reference.jsonl"))
    parser.add_argument("--guide-output", default=str(INTERIM_DIR / "ncpms_openapi_guide.jsonl"))
    return parser.parse_args()


def parse_params(values: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--param must be key=value, got: {value}")
        key, val = value.split("=", 1)
        params[key] = val
    return params


def split_values(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                items.append(part)
    return items


def load_sick_keys(args: argparse.Namespace) -> list[str]:
    keys = split_values(args.sick_key)
    if not args.sick_keys_file:
        return keys

    path = Path(args.sick_keys_file)
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            row = json.loads(line)
            value = row.get("sickKey") or row.get("sick_key")
            if value:
                keys.append(str(value))
            continue
        keys.extend(split_values([line]))
    return keys


def load_insect_keys(args: argparse.Namespace) -> list[str]:
    keys = split_values(args.insect_key)
    if not args.insect_keys_file:
        return keys

    path = Path(args.insect_keys_file)
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            row = json.loads(line)
            value = row.get("insectKey") or row.get("insect_key")
            if value:
                keys.append(str(value))
            continue
        keys.extend(split_values([line]))
    return keys


def load_dgnss_req_nos(args: argparse.Namespace) -> list[str]:
    keys = split_values(args.dgnss_req_no)
    if not args.dgnss_req_nos_file:
        return keys

    path = Path(args.dgnss_req_nos_file)
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            row = json.loads(line)
            value = row.get("dgnssReqNo") or row.get("dgnss_req_no")
            if value:
                keys.append(str(value))
            continue
        keys.extend(split_values([line]))
    return keys


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xml_to_obj(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return normalize_text(element.text or "")

    data: dict[str, Any] = {}
    text = normalize_text(element.text or "")
    if text:
        data["_text"] = text

    for child in children:
        key = strip_namespace(child.tag)
        value = xml_to_obj(child)
        if key in data:
            if not isinstance(data[key], list):
                data[key] = [data[key]]
            data[key].append(value)
        else:
            data[key] = value
    return data


def has_record_signature(row: dict[str, Any]) -> bool:
    return any(key in row for key in GENERIC_RECORD_KEYS)


def extract_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        records: list[dict[str, Any]] = []
        for item in value:
            records.extend(extract_records(item))
        return records

    if not isinstance(value, dict):
        return []

    if has_record_signature(value):
        return [value]

    preferred_keys = ["item", "items", "row", "rows", "list", "data", "result", "body", "response"]
    for key in preferred_keys:
        if key not in value:
            continue
        records = extract_records(value[key])
        if records:
            return records

    records = []
    for child in value.values():
        records.extend(extract_records(child))
    return records


def parse_api_records(raw: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        try:
            parsed = xml_to_obj(ET.fromstring(raw.strip()))
        except ET.ParseError:
            return [{"raw_text": raw}]

    records = extract_records(parsed)
    if records:
        return records
    if isinstance(parsed, dict):
        return [parsed]
    return [{"raw_text": raw}]


def stringify(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return normalize_text("\n".join(part for part in (stringify(item) for item in value) if part))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            text = stringify(item)
            if text:
                parts.append(f"{key}: {text}")
        return normalize_text("\n".join(parts))
    return normalize_text(str(value))


def field(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = stringify(row.get(key))
        if value:
            return value
    return ""


def as_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]


def build_image_notes(row: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for key, label in [
        ("virusImgList", "병원체 사진"),
        ("spcsPhotoData", "곤충 사진"),
        ("imageList", "피해/해충 사진"),
    ]:
        value = row.get(key)
        if not value:
            continue
        if isinstance(value, dict):
            urls = as_list(value.get("image"))
            titles = as_list(value.get("imageTitle"))
            checks = as_list(value.get("iemSpchcknNm"))
            for index, url in enumerate(urls):
                title = stringify(titles[index]) if index < len(titles) else ""
                check_name = stringify(checks[index]) if index < len(checks) else ""
                note = " / ".join(part for part in [title, check_name, stringify(url)] if part)
                if note:
                    notes.append(f"{label}: {note}")
        else:
            text = stringify(value)
            if text:
                notes.append(f"{label}: {text}")
    return notes


def build_image_refs(row: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for key, image_type in [
        ("virusImgList", "pathogen"),
        ("spcsPhotoData", "species"),
        ("imageList", "damage"),
    ]:
        value = row.get(key)
        if not isinstance(value, dict):
            continue
        urls = as_list(value.get("image"))
        titles = as_list(value.get("imageTitle"))
        checks = as_list(value.get("iemSpchcknNm"))
        for index, url in enumerate(urls):
            image_url = stringify(url)
            if not image_url:
                continue
            refs.append(
                {
                    "type": image_type,
                    "url": image_url,
                    "title": stringify(titles[index]) if index < len(titles) else "",
                    "label": stringify(checks[index]) if index < len(checks) else "",
                }
            )
    return refs


def public_url(endpoint_url: str, params: dict[str, Any]) -> str:
    public_params = {key: value for key, value in params.items() if key != "apiKey"}
    if not public_params:
        return endpoint_url
    return f"{endpoint_url}?{urlencode(public_params)}"


def contains_pesticide_text(text: str) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in PESTICIDE_WORDS)


def normalize_disease_detail_record(
    row: dict[str, Any],
    source: dict[str, Any],
    crop: str | None,
    endpoint_url: str | None,
    request_params: dict[str, Any] | None,
) -> dict[str, Any]:
    crop_name = field(row, "cropName", "crop_name", "crop") or crop or ""
    sick_name = field(row, "sickNameKor", "disease_name", "title") or "NCPMS disease detail"
    sick_key = field(row, "sickKey", "sick_key") or stringify((request_params or {}).get("sickKey"))

    sections = [
        ("작물명", crop_name),
        ("병 한글명", sick_name),
        ("병 한문명", field(row, "sickNameChn")),
        ("병 영문명", field(row, "sickNameEng")),
        ("전염경로", field(row, "infectionRoute")),
        ("발생생태", field(row, "developmentCondition")),
        ("병 증상", field(row, "symptoms", "symptom")),
        ("방제방법", field(row, "preventionMethod", "control_note")),
        ("생물학적방제방법", field(row, "biologyPrvnbeMth")),
        ("화학적방제방법", field(row, "chemicalPrvnbeMth")),
        ("기타", field(row, "etc")),
        ("병원체 이름", field(row, "virusName")),
        ("병원체 특징", field(row, "sfeNm")),
    ]
    text_parts = [f"{label}: {value}" for label, value in sections if value]
    image_refs = build_image_refs(row)
    text = normalize_text("\n".join(text_parts))

    tags = list(source.get("safety_tags", []))
    if field(row, "chemicalPrvnbeMth") or contains_pesticide_text(text):
        tags.append("pesticide_caution")

    source_url = (
        row.get("source_url")
        or (public_url(endpoint_url, request_params or {}) if endpoint_url else "")
        or source["url"]
    )
    title_value = " - ".join(part for part in [crop_name, sick_name] if part) or sick_name
    doc_seed = sick_key or title_value or text

    raw_record = dict(row)
    if sick_key and "sickKey" not in raw_record:
        raw_record["sickKey"] = sick_key
    if request_params:
        raw_record["_request_params"] = {key: value for key, value in request_params.items() if key != "apiKey"}

    return {
        "doc_id": f"{source['source_id']}:SVC05:{stable_hash(str(doc_seed))}",
        "source_key": source["source_key"],
        "source_id": source["source_uuid"],
        "title": f"{source['title']} - {title_value}",
        "publisher": source["publisher"],
        "url": source_url,
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": "reference_only",
        "safety_tags": merge_safety_tags(tags),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": [value for value in [crop_name] if value],
        "collected_at": now_iso(),
        "raw_record": raw_record,
        "image_refs": image_refs,
        "text": text,
    }


def normalize_insect_detail_record(
    row: dict[str, Any],
    source: dict[str, Any],
    crop: str | None,
    endpoint_url: str | None,
    request_params: dict[str, Any] | None,
) -> dict[str, Any]:
    crop_name = field(row, "cropName", "crop_name", "crop") or crop or ""
    insect_name = field(row, "insectSpeciesKor", "insectKorName", "pest_name", "title") or "NCPMS insect detail"
    insect_key = stringify((request_params or {}).get("insectKey")) or field(row, "insectKey", "insect_key")

    sections = [
        ("작물명", crop_name),
        ("해충 한국종명", insect_name),
        ("해충 종명", field(row, "insectSpecies", "speciesName")),
        ("해충 목명", field(row, "insectOrder")),
        ("해충 과명", field(row, "insectFamily")),
        ("해충 속명", field(row, "insectGenus")),
        ("분포정보", field(row, "distrbInfo")),
        ("형태정보", field(row, "stleInfo")),
        ("검역정보", field(row, "qrantInfo")),
        ("생태정보", field(row, "ecologyInfo")),
        ("피해정보", field(row, "damageInfo")),
        ("방제방법", field(row, "preventMethod", "preventionMethod", "control_note")),
        ("생물학적 방제방법", field(row, "biologyPrvnbeMth")),
        ("화학적 방제방법", field(row, "chemicalPrvnbeMth")),
        ("천적곤충 한국종명", field(row, "enemyInsectSpeciesKor")),
        ("천적곤충 종명", field(row, "enemyInsectSpecies")),
        ("천적곤충 목명", field(row, "enemyInsectOrder")),
        ("천적곤충 과명", field(row, "enemyInsectFamily")),
    ]
    text_parts = [f"{label}: {value}" for label, value in sections if value]
    image_refs = build_image_refs(row)
    text = normalize_text("\n".join(text_parts))

    tags = list(source.get("safety_tags", []))
    if field(row, "chemicalPrvnbeMth") or contains_pesticide_text(text):
        tags.append("pesticide_caution")

    source_url = (
        row.get("source_url")
        or field(row, "insectLink")
        or (public_url(endpoint_url, request_params or {}) if endpoint_url else "")
        or source["url"]
    )
    title_value = " - ".join(part for part in [crop_name, insect_name] if part) or insect_name
    doc_seed = insect_key or title_value or text

    raw_record = dict(row)
    if insect_key and "_detail_insectKey" not in raw_record:
        raw_record["_detail_insectKey"] = insect_key
    if request_params:
        raw_record["_request_params"] = {key: value for key, value in request_params.items() if key != "apiKey"}

    return {
        "doc_id": f"{source['source_id']}:SVC07:{stable_hash(str(doc_seed))}",
        "source_key": source["source_key"],
        "source_id": source["source_uuid"],
        "title": f"{source['title']} - {title_value}",
        "publisher": source["publisher"],
        "url": source_url,
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": "reference_only",
        "safety_tags": merge_safety_tags(tags),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": [value for value in [crop_name] if value],
        "collected_at": now_iso(),
        "raw_record": raw_record,
        "image_refs": image_refs,
        "text": text,
    }


def normalize_consult_detail_record(
    row: dict[str, Any],
    source: dict[str, Any],
    crop: str | None,
    endpoint_url: str | None,
    request_params: dict[str, Any] | None,
) -> dict[str, Any]:
    crop_name = field(row, "cropName", "crop_name", "crop") or crop or ""
    title = field(row, "dgnssReqSj", "title") or "NCPMS consultation case"
    dgnss_req_no = field(row, "dgnssReqNo", "dgnss_req_no") or stringify((request_params or {}).get("dgnssReqNo"))

    location = " ".join(
        part for part in [field(row, "sidoName"), field(row, "sigunguName"), field(row, "emdName")] if part
    )
    sections = [
        ("상담제목", title),
        ("작물명", crop_name),
        ("신청일자", field(row, "registDatetm")),
        ("분야", field(row, "realm")),
        ("지역", location),
        ("최초발생일", field(row, "occrrncDatetm")),
        ("주요 발병부위", field(row, "priyClName")),
        ("증상 및 특이사항", field(row, "reqestCn")),
        ("답변일자", field(row, "answerDatetm")),
        ("답변구분", field(row, "answerSe")),
        ("답변자", field(row, "answrrName")),
        ("병해충", field(row, "dbyhs")),
        ("진단소견", field(row, "dgnssOpin")),
        ("방제법", field(row, "prvnbeMth")),
    ]
    text_parts = [f"{label}: {value}" for label, value in sections if value]
    image_refs = build_image_refs(row)
    text = normalize_text("\n".join(text_parts))

    tags = list(source.get("safety_tags", []))
    tags.append("expert_case_reference")
    if field(row, "prvnbeMth") or contains_pesticide_text(text):
        tags.append("pesticide_caution")

    source_url = row.get("source_url") or (public_url(endpoint_url, request_params or {}) if endpoint_url else "") or source["url"]
    title_value = " - ".join(part for part in [crop_name, title] if part) or title
    doc_seed = dgnss_req_no or title_value or text

    raw_record = dict(row)
    if dgnss_req_no and "dgnssReqNo" not in raw_record:
        raw_record["dgnssReqNo"] = dgnss_req_no
    if request_params:
        raw_record["_request_params"] = {key: value for key, value in request_params.items() if key != "apiKey"}

    return {
        "doc_id": f"{source['source_id']}:SVC42:{stable_hash(str(doc_seed))}",
        "source_key": source["source_key"],
        "source_id": source["source_uuid"],
        "title": f"{source['title']} - {title_value}",
        "publisher": source["publisher"],
        "url": source_url,
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": "expert_case_reference",
        "safety_tags": merge_safety_tags(tags),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": [value for value in [crop_name] if value],
        "collected_at": now_iso(),
        "raw_record": raw_record,
        "image_refs": image_refs,
        "text": text,
    }


def normalize_generic_record(
    row: dict[str, Any],
    source: dict[str, Any],
    crop: str | None,
    endpoint_url: str | None = None,
    request_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text_parts = []
    for key in [
        "crop",
        "crop_name",
        "cropName",
        "pest_name",
        "insectKorName",
        "speciesName",
        "dgnssReqSj",
        "reqestCn",
        "dgnssOpin",
        "divCode",
        "divName",
        "cropCode",
        "korName",
        "oprName",
        "detailUrl",
        "disease_name",
        "sickNameKor",
        "symptom",
        "symptoms",
        "description",
        "occurrence_condition",
        "developmentCondition",
        "observation_point",
        "control_note",
        "preventionMethod",
        "chemicalPrvnbeMth",
        "caution",
    ]:
        if row.get(key):
            text_parts.append(f"{key}: {stringify(row[key])}")

    if not text_parts:
        text_parts = [f"{key}: {stringify(value)}" for key, value in row.items() if stringify(value)]

    text = normalize_text("\n".join(text_parts))
    title_value = (
        field(
            row,
            "pest_name",
            "insectKorName",
            "speciesName",
            "dgnssReqSj",
            "korName",
            "oprName",
            "disease_name",
            "sickNameKor",
            "title",
        )
        or "NCPMS pest reference"
    )
    tags = list(source.get("safety_tags", []))
    if contains_pesticide_text(text):
        tags.append("pesticide_caution")

    request_url = public_url(endpoint_url, request_params or {}) if endpoint_url else ""
    return {
        "doc_id": f"{source['source_id']}:{stable_hash(text or title_value)}",
        "source_key": source["source_key"],
        "source_id": source["source_uuid"],
        "title": f"{source['title']} - {title_value}",
        "publisher": source["publisher"],
        "url": row.get("source_url") or row.get("detailUrl") or request_url or source["url"],
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": "reference_only",
        "safety_tags": merge_safety_tags(tags),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": [value for value in [crop or field(row, "crop", "crop_name", "cropName")] if value],
        "collected_at": now_iso(),
        "raw_record": row,
        "text": text,
    }


def normalize_record(
    row: dict[str, Any],
    source: dict[str, Any],
    crop: str | None,
    service_code: str | None = None,
    endpoint_url: str | None = None,
    request_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if service_code == "SVC07":
        return normalize_insect_detail_record(row, source, crop, endpoint_url, request_params)
    if service_code == "SVC42":
        return normalize_consult_detail_record(row, source, crop, endpoint_url, request_params)
    if service_code == "SVC05":
        return normalize_disease_detail_record(row, source, crop, endpoint_url, request_params)
    if service_code == "SVC41":
        return normalize_generic_record(row, source, crop, endpoint_url, request_params)
    if any(key in row for key in CONSULT_DETAIL_KEYS):
        return normalize_consult_detail_record(row, source, crop, endpoint_url, request_params)
    if any(key in row for key in INSECT_DETAIL_KEYS):
        return normalize_insect_detail_record(row, source, crop, endpoint_url, request_params)
    if any(key in row for key in DISEASE_DETAIL_KEYS):
        return normalize_disease_detail_record(row, source, crop, endpoint_url, request_params)
    return normalize_generic_record(row, source, crop, endpoint_url, request_params)


def collect_guide(source: dict[str, Any], output: Path) -> None:
    raw_html = http_get_text(source["url"], timeout=30)
    raw_dir = RAW_DIR / source["source_id"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{stable_hash(source['url'])}.html"
    raw_path.write_text(raw_html, encoding="utf-8", newline="\n")

    text = html_to_text(raw_html)
    doc = {
        "doc_id": f"{source['source_id']}:{stable_hash(source['url'])}",
        "source_key": source["source_key"],
        "source_id": source["source_uuid"],
        "title": source["title"],
        "publisher": source["publisher"],
        "url": source["url"],
        "license": source["license"],
        "category": source["category"],
        "priority": source["priority"],
        "usage_scope": "api_contract_reference",
        "safety_tags": merge_safety_tags(source.get("safety_tags")),
        "symptom_keywords": detect_symptom_keywords(text),
        "crop_or_plant": [],
        "collected_at": now_iso(),
        "raw_path": str(raw_path),
        "text": text,
    }
    write_jsonl(output, [doc])


def fetch_endpoint_records(
    endpoint_url: str,
    params: dict[str, Any],
    source: dict[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    raw = http_get_text(endpoint_url, params=params, timeout=30)
    raw_dir = RAW_DIR / source["source_id"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{stable_hash(json.dumps(params, ensure_ascii=False, sort_keys=True))}.txt"
    raw_path.write_text(raw, encoding="utf-8", newline="\n")

    rows = parse_api_records(raw)
    output: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in rows:
        if isinstance(row, dict):
            row = {**row, "_raw_path": str(raw_path)}
            output.append((row, params))
    return output


def extract_sick_keys(records: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[str]:
    keys: list[str] = []
    for row, _request_params in records:
        sick_key = field(row, "sickKey", "sick_key")
        if sick_key and sick_key not in keys:
            keys.append(sick_key)
    return keys


def extract_insect_keys(records: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[str]:
    keys: list[str] = []
    for row, _request_params in records:
        insect_key = field(row, "insectKey", "insect_key")
        if insect_key and insect_key not in keys:
            keys.append(insect_key)
    return keys


def extract_dgnss_req_nos(records: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[str]:
    keys: list[str] = []
    for row, _request_params in records:
        dgnss_req_no = field(row, "dgnssReqNo", "dgnss_req_no")
        if dgnss_req_no and dgnss_req_no not in keys:
            keys.append(dgnss_req_no)
    return keys


def collect_endpoint(
    endpoint_url: str,
    params: dict[str, str],
    source: dict[str, Any],
    crop: str | None,
    service_code: str | None,
    service_type: str | None,
    sick_name_kor: str | None,
    insect_kor_name: str | None,
    dgnss_req_sj: str | None,
    search_name: str | None,
    div_code: str | None,
    crop_code: str | None,
    kor_name: str | None,
    opr_name: str | None,
    sick_keys: list[str],
    insect_keys: list[str],
    dgnss_req_nos: list[str],
    fetch_details: bool,
) -> list[dict[str, Any]]:
    if not NCPMS_API_KEY:
        raise RuntimeError("NCPMS_API_KEY is missing. Set it in .env after OpenAPI approval.")

    base_params: dict[str, Any] = dict(params)
    base_params.setdefault("apiKey", NCPMS_API_KEY)
    if service_code:
        base_params.setdefault("serviceCode", service_code)
    if service_type:
        base_params.setdefault("serviceType", service_type)

    effective_service_code = str(base_params.get("serviceCode") or service_code or "")
    if effective_service_code == "SVC01":
        base_params.setdefault("serviceType", "AA003")
        if crop:
            base_params.setdefault("cropName", crop)
        if sick_name_kor:
            base_params.setdefault("sickNameKor", sick_name_kor)
    elif effective_service_code == "SVC03":
        base_params.setdefault("serviceType", "AA003")
        if crop:
            base_params.setdefault("cropName", crop)
        if insect_kor_name:
            base_params.setdefault("insectKorName", insect_kor_name)
    elif effective_service_code == "SVC41":
        base_params.setdefault("serviceType", "AA003")
        if crop:
            base_params.setdefault("cropName", crop)
        if dgnss_req_sj:
            base_params.setdefault("dgnssReqSj", dgnss_req_sj)
    elif effective_service_code == "SVC42":
        base_params.setdefault("serviceType", "AA003")
    elif effective_service_code == "SVC16":
        base_params.setdefault("serviceType", "AA003")
        if crop:
            base_params.setdefault("cropName", crop)
        if search_name:
            base_params.setdefault("searchName", search_name)
        if div_code:
            base_params.setdefault("divCode", div_code)
        if crop_code:
            base_params.setdefault("cropCode", crop_code)
        if kor_name:
            base_params.setdefault("korName", kor_name)
        if opr_name:
            base_params.setdefault("oprName", opr_name)
    elif crop:
        base_params.setdefault("crop", crop)

    if effective_service_code == "SVC01" and not (base_params.get("cropName") or base_params.get("sickNameKor")):
        raise ValueError("NCPMS SVC01 disease search requires --crop, --sick-name-kor, or matching --param.")
    if effective_service_code == "SVC03" and not (base_params.get("cropName") or base_params.get("insectKorName")):
        raise ValueError("NCPMS SVC03 insect search requires --crop, --insect-kor-name, or matching --param.")
    if effective_service_code == "SVC41" and not (base_params.get("cropName") or base_params.get("dgnssReqSj")):
        raise ValueError("NCPMS SVC41 consultation search requires --crop, --dgnss-req-sj, or matching --param.")
    if effective_service_code == "SVC05" and not sick_keys and "sickKey" not in base_params:
        raise ValueError("NCPMS SVC05 disease detail requires --sick-key or --sick-keys-file.")
    if effective_service_code == "SVC07" and not insect_keys and "insectKey" not in base_params:
        raise ValueError("NCPMS SVC07 insect detail requires --insect-key or --insect-keys-file.")
    if effective_service_code == "SVC42" and not dgnss_req_nos and "dgnssReqNo" not in base_params:
        raise ValueError("NCPMS SVC42 consultation detail requires --dgnss-req-no or --dgnss-req-nos-file.")

    requested: list[tuple[dict[str, Any], dict[str, Any]]] = []
    if effective_service_code == "SVC01":
        search_records = fetch_endpoint_records(endpoint_url, base_params, source)
        if not fetch_details:
            requested.extend(search_records)
        else:
            discovered_keys = extract_sick_keys(search_records)
            for sick_key in discovered_keys:
                request_params = {"apiKey": NCPMS_API_KEY, "serviceCode": "SVC05", "sickKey": sick_key}
                requested.extend(fetch_endpoint_records(endpoint_url, request_params, source))
            effective_service_code = "SVC05"
    elif effective_service_code == "SVC03":
        search_records = fetch_endpoint_records(endpoint_url, base_params, source)
        if not fetch_details:
            requested.extend(search_records)
        else:
            discovered_keys = extract_insect_keys(search_records)
            for insect_key in discovered_keys:
                request_params = {"apiKey": NCPMS_API_KEY, "serviceCode": "SVC07", "insectKey": insect_key}
                requested.extend(fetch_endpoint_records(endpoint_url, request_params, source))
            effective_service_code = "SVC07"
    elif effective_service_code == "SVC41":
        search_records = fetch_endpoint_records(endpoint_url, base_params, source)
        if not fetch_details:
            requested.extend(search_records)
        else:
            discovered_keys = extract_dgnss_req_nos(search_records)
            for dgnss_req_no in discovered_keys:
                request_params = {
                    "apiKey": NCPMS_API_KEY,
                    "serviceCode": "SVC42",
                    "serviceType": "AA003",
                    "dgnssReqNo": dgnss_req_no,
                }
                requested.extend(fetch_endpoint_records(endpoint_url, request_params, source))
            effective_service_code = "SVC42"
    elif sick_keys:
        for sick_key in sick_keys:
            request_params = dict(base_params)
            request_params["sickKey"] = sick_key
            requested.extend(fetch_endpoint_records(endpoint_url, request_params, source))
    elif insect_keys:
        for insect_key in insect_keys:
            request_params = dict(base_params)
            request_params["insectKey"] = insect_key
            requested.extend(fetch_endpoint_records(endpoint_url, request_params, source))
    elif dgnss_req_nos:
        for dgnss_req_no in dgnss_req_nos:
            request_params = dict(base_params)
            request_params["dgnssReqNo"] = dgnss_req_no
            requested.extend(fetch_endpoint_records(endpoint_url, request_params, source))
    else:
        requested.extend(fetch_endpoint_records(endpoint_url, base_params, source))

    return [
        normalize_record(row, source, crop, effective_service_code, endpoint_url, request_params)
        for row, request_params in requested
    ]


def main() -> None:
    args = parse_args()
    ensure_dirs()
    registry = load_source_registry()
    source = registry["ncpms_pest_reference"]
    guide_source = registry["ncpms_openapi_guide"]

    if not args.skip_guide:
        collect_guide(guide_source, Path(args.guide_output))

    sick_keys = load_sick_keys(args)
    insect_keys = load_insect_keys(args)
    dgnss_req_nos = load_dgnss_req_nos(args)
    service_code = args.service_code or (
        "SVC05"
        if sick_keys
        else "SVC07"
        if insect_keys
        else "SVC42"
        if dgnss_req_nos
        else "SVC41"
        if args.dgnss_req_sj
        else "SVC16"
        if args.search_name or args.div_code or args.crop_code or args.kor_name or args.opr_name
        else "SVC03"
        if args.insect_kor_name
        else "SVC01"
        if args.sick_name_kor or args.fetch_details
        else None
    )

    if args.manual_jsonl:
        rows = read_jsonl(Path(args.manual_jsonl))[: args.limit]
        docs = [normalize_record(row, source, args.crop, service_code) for row in rows]
    elif args.endpoint_url or service_code:
        docs = collect_endpoint(
            endpoint_url=args.endpoint_url or DEFAULT_ENDPOINT_URL,
            params=parse_params(args.param),
            source=source,
            crop=args.crop,
            service_code=service_code,
            service_type=args.service_type,
            sick_name_kor=args.sick_name_kor,
            insect_kor_name=args.insect_kor_name,
            dgnss_req_sj=args.dgnss_req_sj,
            search_name=args.search_name,
            div_code=args.div_code,
            crop_code=args.crop_code,
            kor_name=args.kor_name,
            opr_name=args.opr_name,
            sick_keys=sick_keys,
            insect_keys=insect_keys,
            dgnss_req_nos=dgnss_req_nos,
            fetch_details=args.fetch_details,
        )[: args.limit]
    else:
        docs = []
        print(
            "NCPMS guide was collected. Pest records were not collected because no --manual-jsonl, "
            "--endpoint-url, or --sick-key was provided."
        )

    count = write_jsonl(Path(args.output), docs)
    print(f"Prepared {count} NCPMS pest reference documents: {args.output}")


if __name__ == "__main__":
    main()
