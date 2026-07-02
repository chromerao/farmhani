"""RAG 자동 평가 (LLM-as-a-Judge) 확장판

기존 평가 시스템 대비 확장 내용:
  1. 근거 문서 표기: 파이프라인이 답변 생성 시 실제로 사용한 검색 문서(rerank 이후)를
     캡처하여 리포트에 제목/출처/유사도/발췌와 함께 기록합니다.
     (기존에는 평가용으로 검색을 한 번 더 돌려 실제 파이프라인 결과와 달랐음)
  2. 가상 이미지 평가: 표준 라이브러리만으로 합성 잎 PNG(황화/반점/건강)를 생성하고,
     Supabase signed URL 대신 base64 data URL을 주입해 실제 Vision 모델로
     멀티모달 진단 흐름 전체를 평가합니다.
     이미지 케이스는 '사진반영(Image Grounding)' 지표가 추가됩니다.

파이프라인 코드는 수정하지 않고, 이 스크립트 안에서 런타임 패치로만 처리합니다.

실행:
    cd backend
    python scripts/evaluate_rag.py                # 전체 평가
    python scripts/evaluate_rag.py --ids image_1  # 특정 케이스만
    python scripts/evaluate_rag.py --skip-images  # 텍스트 케이스만
"""

import argparse
import base64
import json
import math
import os
import struct
import sys
import uuid
import zlib
from datetime import datetime
from pathlib import Path

# 상위 폴더(backend)를 패스에 추가하여 app 모듈 import가 되도록 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_DIR / "tests"
IMAGE_DIR = TESTS_DIR / "eval_images"

from openai import OpenAI

from app.core.config import settings
from app.services.rag import pipeline
from app.services.rag import vision

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL") or "gpt-4o-mini"


# ---------------------------------------------------------------------------
# 경량 Supabase 대체물 (파이프라인 구동용, 실제 검색은 vectorstore가 수행)
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self._op = None
        self._payload = None
        self._filters = []
        self._like_filters = []
        self._order = None
        self._limit = None

    def select(self, *args, **kwargs):
        self._op = "select"
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def eq(self, field, value):
        self._filters.append((field, str(value)))
        return self

    def like(self, field, pattern):
        self._like_filters.append((field, str(pattern)))
        return self

    def order(self, field, desc=False):
        self._order = (field, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        return self

    def execute(self):
        if self._op == "insert":
            rows = self._payload if isinstance(self._payload, list) else [self._payload]
            self.db.tables.setdefault(self.name, []).extend(rows)
            self.db.inserts.append((self.name, self._payload))
            return _Resp(rows)
        if self._op == "update":
            self.db.updates.append((self.name, self._payload, dict(self._filters)))
            return _Resp([])
        if self._op == "select":
            rows = [
                r for r in self.db.tables.get(self.name, [])
                if all(str(r.get(f)) == v for f, v in self._filters)
            ]
            for field, pattern in self._like_filters:
                prefix = pattern[:-1] if pattern.endswith("%") else pattern
                rows = [r for r in rows if str(r.get(field) or "").startswith(prefix)]
            if self._order:
                field, desc = self._order
                rows = sorted(rows, key=lambda r: str(r.get(field) or ""), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            return _Resp(rows)
        return _Resp([])


class FakeDB:
    """table()만 지원하는 초경량 Supabase 대체물."""

    def __init__(self, tables=None):
        self.tables = tables or {}
        self.inserts = []
        self.updates = []

    def table(self, name):
        return _FakeTable(name, self)


# ---------------------------------------------------------------------------
# 합성(가상) 잎 이미지 생성 - 표준 라이브러리만 사용 (Pillow 불필요)
# ---------------------------------------------------------------------------
def _write_png(path: Path, width: int, height: int, pixels):
    """pixels: 행 단위 (r, g, b) 튜플 리스트."""
    raw = b"".join(
        b"\x00" + bytes(channel for px in row for channel in px)
        for row in pixels
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _clamp(value: float) -> int:
    return max(0, min(255, int(value)))


def _blend(base, target, weight: float):
    weight = max(0.0, min(1.0, weight))
    return tuple(_clamp(b + (t - b) * weight) for b, t in zip(base, target))


def _clamp_px(color, noise):
    return tuple(_clamp(channel + noise) for channel in color)


def generate_leaf_image(path: Path, variant: str, size: int = 384):
    """단순한 잎 모양 합성 이미지를 생성합니다.

    variant:
      - "yellow_edges": 잎 가장자리/잎끝 황화
      - "brown_spots" : 잎 표면 갈색 원형 반점
      - "healthy"     : 특이 증상 없는 초록 잎
    """
    bg = (244, 242, 236)
    green = (58, 132, 66)
    vein = (38, 102, 50)
    yellow = (216, 192, 66)
    brown = (108, 64, 36)
    ring = (168, 128, 52)

    cx = size / 2
    y0, y1 = size * 0.10, size * 0.88
    w_max = size * 0.29
    spots = [
        (0.42, 0.30, 0.045), (0.58, 0.48, 0.055), (0.46, 0.62, 0.038),
        (0.55, 0.24, 0.032), (0.44, 0.45, 0.030),
    ]  # (x비율, y비율, 반지름비율)

    rows = []
    for y in range(size):
        row = []
        t = (y - y0) / (y1 - y0)
        half = w_max * (math.sin(math.pi * t) ** 0.85) if 0.0 < t < 1.0 else 0.0
        for x in range(size):
            noise = ((x * 1103515245 + y * 12345) >> 8) % 13 - 6
            dx = abs(x - cx)
            # 잎자루(줄기)
            if y1 <= y < y1 + size * 0.07 and dx <= 3:
                row.append(_clamp_px((96, 118, 66), noise))
                continue
            if half <= 1.0 or dx > half:
                row.append(_clamp_px(bg, noise // 3))
                continue

            edge_frac = dx / half
            color = green
            if variant == "yellow_edges":
                if edge_frac > 0.62:
                    color = _blend(green, yellow, (edge_frac - 0.62) / 0.38 * 1.2)
                if t < 0.14 or t > 0.86:
                    color = _blend(color, yellow, 0.75)
            # 중앙 잎맥
            if dx <= 2 and color == green:
                color = vein
            if variant == "brown_spots":
                px, py = x / size, y / size
                for sx, sy, sr in spots:
                    dist = math.hypot(px - sx, py - sy)
                    if dist <= sr:
                        color = brown
                        break
                    if dist <= sr * 1.35:
                        color = _blend(color, ring, 0.8)
                        break
            row.append(_clamp_px(color, noise))
        rows.append(row)
    _write_png(path, size, size, rows)


IMAGE_VARIANTS = {
    "leaf_yellow_edges.png": "yellow_edges",
    "leaf_brown_spots.png": "brown_spots",
    "leaf_healthy.png": "healthy",
}


def ensure_eval_images():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    for filename, variant in IMAGE_VARIANTS.items():
        target = IMAGE_DIR / filename
        if not target.exists():
            generate_leaf_image(target, variant)
            print(f"  합성 이미지 생성: {target.name}")


# ---------------------------------------------------------------------------
# 런타임 패치 1: Vision signed URL -> 로컬 합성 이미지 data URL
# ---------------------------------------------------------------------------
_original_signed_url = vision.create_signed_image_url


def _local_signed_url(db, storage_path: str) -> str:
    local = IMAGE_DIR / Path(storage_path).name
    if local.exists():
        encoded = base64.b64encode(local.read_bytes()).decode()
        return f"data:image/png;base64,{encoded}"
    return _original_signed_url(db, storage_path)


# ---------------------------------------------------------------------------
# 런타임 패치 2: generate_answer 직전 상태를 캡처 (실제 사용된 근거 문서 확보)
# ---------------------------------------------------------------------------
_capture: dict = {}
_original_generate_answer = pipeline.generate_answer


def _capturing_generate_answer(state):
    _capture["retrieved_docs"] = [dict(d) for d in state.get("retrieved_docs") or []]
    _capture["search_query"] = state.get("search_query") or ""
    _capture["image_description"] = state.get("image_description") or ""
    _capture["image_signals"] = list(state.get("image_signals") or [])
    _capture["vision_error"] = state.get("vision_error")
    return _original_generate_answer(state)


def apply_patches():
    vision.create_signed_image_url = _local_signed_url
    pipeline.generate_answer = _capturing_generate_answer


# ---------------------------------------------------------------------------
# LLM-as-a-Judge
# ---------------------------------------------------------------------------
EVALUATOR_PROMPT_BASE = """당신은 식물 관리 챗봇 RAG 시스템의 품질을 평가하는 심판(Judge)입니다.
다음 기준에 따라 1점부터 5점까지 점수를 매겨주세요.
반드시 JSON 형식으로 응답해야 합니다.

[평가 지표]
1. Faithfulness (사실성): 생성된 답변이 온전히 '검색된 문서(Context)'에만 기반하고 있습니까? 없는 내용을 지어내지 않았습니까? (문서가 없는데 없다며 올바르게 거절한 경우 5점)
2. Answer Relevance (답변 관련성): 답변이 '사용자의 질문'에 직접적으로 도움을 주며 의도에 부합합니까? (거절해야 할 질문을 잘 거절했어도 5점)
3. Context Relevance (검색 정확도): '검색된 문서'가 질문에 답하기 위해 유용한 정보를 포함하고 있습니까? (거절해야 할 질문은 문서가 없거나 무관해야 5점)
"""

EVALUATOR_SCHEMA_TEXT = """
[JSON 스키마]
{
  "faithfulness_score": int (1~5),
  "faithfulness_reason": str,
  "answer_relevance_score": int (1~5),
  "answer_relevance_reason": str,
  "context_relevance_score": int (1~5),
  "context_relevance_reason": str
}
"""

EVALUATOR_IMAGE_EXTRA = """4. Image Grounding (사진 반영): 답변이 '사진 분석 결과'에서 관찰된 증상을 실제로 반영하여 진단/가이드에 활용하고 있습니까? (사진에 이상이 없는데 이상 없다고 답한 경우도 5점)
"""

EVALUATOR_SCHEMA_IMAGE = """
[JSON 스키마]
{
  "faithfulness_score": int (1~5),
  "faithfulness_reason": str,
  "answer_relevance_score": int (1~5),
  "answer_relevance_reason": str,
  "context_relevance_score": int (1~5),
  "context_relevance_reason": str,
  "image_grounding_score": int (1~5),
  "image_grounding_reason": str
}
"""


def judge_answer(client: OpenAI, item, answer_text, context_text, image_description=None):
    is_image_case = image_description is not None
    system_prompt = EVALUATOR_PROMPT_BASE
    if is_image_case:
        system_prompt += EVALUATOR_IMAGE_EXTRA + EVALUATOR_SCHEMA_IMAGE
    else:
        system_prompt += EVALUATOR_SCHEMA_TEXT

    user_prompt = (
        f"사용자 질문: {item['question']}\n\n"
        f"기대 개념(참고): {item.get('expected_concept', '')}\n\n"
        f"검색된 문서(Context): {context_text}\n\n"
    )
    if is_image_case:
        user_prompt += f"사진 분석 결과(Vision): {image_description or '분석 결과 없음'}\n\n"
    user_prompt += f"RAG 시스템이 생성한 답변: {answer_text}\n"

    try:
        res = client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return json.loads(res.choices[0].message.content)
    except Exception as exc:  # noqa: BLE001
        print(f"  평가 실패: {exc}")
        fallback = {
            "faithfulness_score": 1, "faithfulness_reason": str(exc),
            "answer_relevance_score": 1, "answer_relevance_reason": str(exc),
            "context_relevance_score": 1, "context_relevance_reason": str(exc),
        }
        if is_image_case:
            fallback["image_grounding_score"] = 1
            fallback["image_grounding_reason"] = str(exc)
        return fallback


# ---------------------------------------------------------------------------
# 평가 실행
# ---------------------------------------------------------------------------
def _excerpt(text: str, max_len: int = 120) -> str:
    clean = " ".join(str(text or "").split()).replace("|", "/")
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rstrip() + "..."


def build_fake_db(plant_id: str, user_id: str, photo=None) -> FakeDB:
    tables = {
        "plants": [{
            "id": plant_id, "user_id": user_id,
            "name": "테스트식물", "species": "알 수 없음",
        }],
        "care_logs": [],
        "plant_photos": [photo] if photo else [],
        "chat_sessions": [],
        "chat_messages": [],
    }
    return FakeDB(tables)


def run_single_case(client: OpenAI, item) -> dict:
    user_id = str(uuid.uuid4())
    plant_id = str(uuid.uuid4())
    photo_id = None
    photo = None
    is_image_case = bool(item.get("image_file"))

    if is_image_case:
        photo_id = str(uuid.uuid4())
        photo = {
            "id": photo_id,
            "plant_id": plant_id,
            "storage_path": f"eval-images/{item['image_file']}",
            "note": None,
            "captured_at": datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now().isoformat(),
        }

    fake_db = build_fake_db(plant_id, user_id, photo)
    _capture.clear()

    try:
        final_answer = pipeline.run_rag_workflow(
            db_client=fake_db,
            user_id=user_id,
            plant_id=plant_id,
            care_log_id=None,
            photo_id=photo_id,
            question=item["question"],
            new_session=True,
        )
        answer_text = (
            f"요약: {final_answer.get('summary', '')}\n"
            f"원인 후보: {', '.join(final_answer.get('possibleCauses', []))}\n"
            f"오늘 할 일: {', '.join(final_answer.get('todayActions', []))}"
        )
        citations = final_answer.get("citations") or []
    except Exception as exc:  # noqa: BLE001
        print(f"  파이프라인 에러: {exc}")
        answer_text = f"에러 발생: {exc}"
        citations = []

    retrieved_docs = _capture.get("retrieved_docs") or []
    search_query = _capture.get("search_query") or ""
    image_description = _capture.get("image_description") or ""
    image_signals = _capture.get("image_signals") or []
    vision_error = _capture.get("vision_error")

    if retrieved_docs:
        context_text = "\n\n".join(
            f"[문서 {i + 1}] {(d.get('metadata') or {}).get('title') or '출처 미상'}\n{str(d.get('content') or '')[:800]}"
            for i, d in enumerate(retrieved_docs)
        )
    else:
        context_text = "검색된 문서 없음"

    eval_data = judge_answer(
        client, item, answer_text, context_text,
        image_description=(image_description or "분석 결과 없음") if is_image_case else None,
    )

    return {
        "id": item["id"],
        "type": item["type"],
        "question": item["question"],
        "is_image_case": is_image_case,
        "image_file": item.get("image_file"),
        "answer": answer_text,
        "citations": citations,
        "retrieved_docs": retrieved_docs,
        "search_query": search_query,
        "image_description": image_description,
        "image_signals": image_signals,
        "vision_error": vision_error,
        "eval_data": eval_data,
    }


# ---------------------------------------------------------------------------
# 리포트 생성 (Markdown)
# ---------------------------------------------------------------------------
def _avg(scores):
    return sum(scores) / len(scores) if scores else 0.0


def write_report(results, report_path: Path):
    f_scores = [r["eval_data"].get("faithfulness_score", 0) for r in results]
    a_scores = [r["eval_data"].get("answer_relevance_score", 0) for r in results]
    c_scores = [r["eval_data"].get("context_relevance_score", 0) for r in results]
    i_scores = [
        r["eval_data"].get("image_grounding_score", 0)
        for r in results if r["is_image_case"] and "image_grounding_score" in r["eval_data"]
    ]

    lines = []
    lines.append("# RAG 자동 평가(LLM-as-a-Judge) 리포트\n")
    lines.append(f"평가 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"케이스 수: 전체 {len(results)}개 (텍스트 {sum(1 for r in results if not r['is_image_case'])}개, 이미지 {sum(1 for r in results if r['is_image_case'])}개)\n")

    lines.append("## 📊 전체 요약 (5점 만점)\n")
    lines.append(f"- **평균 사실성(Faithfulness):** {_avg(f_scores):.2f} 점")
    lines.append(f"- **평균 답변 관련성(Answer Relevance):** {_avg(a_scores):.2f} 점")
    lines.append(f"- **평균 검색 정확도(Context Relevance):** {_avg(c_scores):.2f} 점")
    if i_scores:
        lines.append(f"- **평균 사진 반영(Image Grounding, 이미지 케이스 한정):** {_avg(i_scores):.2f} 점")
    lines.append("\n---\n")

    for r in results:
        ev = r["eval_data"]
        lines.append(f"### [{r['id']}] {r['question']} `[{r['type']}]`\n")
        lines.append(f"**답변:** {r['answer']}\n")

        if r["is_image_case"]:
            lines.append(f"**📷 입력 이미지:** `{r['image_file']}` (합성 이미지)\n")
            lines.append(f"**📷 사진 분석(Vision):** {r['image_description'] or '분석 결과 없음'}")
            if r["image_signals"]:
                for signal in r["image_signals"]:
                    lines.append(f"  - {signal}")
            if r["vision_error"]:
                lines.append(f"  - ⚠️ Vision 오류: {r['vision_error']}")
            lines.append("")

        if r["search_query"]:
            lines.append(f"**🔎 검색 쿼리:** {_excerpt(r['search_query'], 200)}\n")

        docs = r["retrieved_docs"]
        if docs:
            lines.append(f"**📚 근거 문서 (파이프라인이 실제 사용한 검색 결과 {len(docs)}건):**\n")
            lines.append("| # | 제목 | source_id | 점수 | 발췌 |")
            lines.append("|---|------|-----------|------|------|")
            for i, doc in enumerate(docs, start=1):
                meta = doc.get("metadata") or {}
                title = _excerpt(meta.get("title") or "출처 미상", 40)
                source_id = _excerpt(meta.get("source_id") or meta.get("sourceId") or "-", 40)
                score = doc.get("score")
                score_text = f"{score:.3f}" if isinstance(score, (int, float)) else "-"
                excerpt = _excerpt(doc.get("content") or "", 100)
                lines.append(f"| {i} | {title} | {source_id} | {score_text} | {excerpt} |")
            lines.append("")
        else:
            lines.append("**📚 근거 문서:** 검색된 문서 없음\n")

        if r["citations"]:
            citation_labels = []
            for cit in r["citations"]:
                label = cit.get("title") or cit.get("sourceId") or "출처 미상"
                citation_labels.append(f"{label} ({cit.get('sourceId', '-')})")
            lines.append(f"**🔗 답변 인용(citations):** {', '.join(citation_labels)}\n")

        lines.append(f"- **사실성(F): {ev.get('faithfulness_score', '-')}/5** - {ev.get('faithfulness_reason', '')}")
        lines.append(f"- **관련성(A): {ev.get('answer_relevance_score', '-')}/5** - {ev.get('answer_relevance_reason', '')}")
        lines.append(f"- **검색정확도(C): {ev.get('context_relevance_score', '-')}/5** - {ev.get('context_relevance_reason', '')}")
        if r["is_image_case"] and "image_grounding_score" in ev:
            lines.append(f"- **사진반영(I): {ev.get('image_grounding_score', '-')}/5** - {ev.get('image_grounding_reason', '')}")
        lines.append("\n---\n")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def evaluate_rag_pipeline(ids=None, skip_images=False):
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY 환경변수가 필요합니다.")
        return

    apply_patches()
    client = OpenAI(api_key=OPENAI_API_KEY)

    dataset_path = TESTS_DIR / "eval_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if ids:
        dataset = [item for item in dataset if item["id"] in ids]
    if skip_images:
        dataset = [item for item in dataset if not item.get("image_file")]

    if any(item.get("image_file") for item in dataset):
        print("가상 이미지 준비 중...")
        ensure_eval_images()

    results = []
    print(f"총 {len(dataset)}개의 데이터 평가를 시작합니다...")

    for i, item in enumerate(dataset):
        print(f"\n[{i + 1}/{len(dataset)}] 타입: {item['type']} | 질문: {item['question']}")
        result = run_single_case(client, item)
        results.append(result)
        ev = result["eval_data"]
        score_line = (
            f" > 점수: F({ev.get('faithfulness_score', '-')}) "
            f"A({ev.get('answer_relevance_score', '-')}) "
            f"C({ev.get('context_relevance_score', '-')})"
        )
        if result["is_image_case"] and "image_grounding_score" in ev:
            score_line += f" I({ev.get('image_grounding_score', '-')})"
        print(score_line + f" | 근거 문서 {len(result['retrieved_docs'])}건")

    report_path = TESTS_DIR / f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    write_report(results, report_path)
    print(f"\n평가 완료! 리포트가 생성되었습니다: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG 자동 평가 (근거 문서 + 가상 이미지 확장판)")
    parser.add_argument("--ids", help="쉼표로 구분한 케이스 id (예: single_1,image_1)")
    parser.add_argument("--skip-images", action="store_true", help="이미지 케이스 제외")
    args = parser.parse_args()

    case_ids = set(args.ids.split(",")) if args.ids else None
    evaluate_rag_pipeline(ids=case_ids, skip_images=args.skip_images)
