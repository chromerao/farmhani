import os
import uuid
import logging
import re
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, date, timezone
from supabase import Client

from app.core.config import settings
from app.services.rag.vectorstore import search_documents
from app.services.rag.vision import VisionAnalysisError, analyze_plant_image
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


def make_excerpt(text: str, max_len: int = 220) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rstrip() + "..."


def is_smalltalk_question(question: str) -> bool:
    normalized = " ".join((question or "").strip().lower().split())
    if not normalized:
        return True
    greetings = {
        "hi",
        "hello",
        "hey",
        "안녕",
        "안녕하세요",
        "안녕?",
        "안녕하세요?",
        "고마워",
        "감사합니다",
    }
    return normalized in greetings or (len(normalized) <= 8 and any(word in normalized for word in greetings))


def extract_user_name(text: str) -> Optional[str]:
    patterns = [
        r"(?:내\s*이름은|제\s*이름은)\s*([가-힣A-Za-z0-9_]{2,20}?)(?:이야|야|입니다|이에요|예요|라고|$)",
        r"(?:나는|전|저는)\s*([가-힣A-Za-z0-9_]{2,20}?)(?:이야|야|입니다|이에요|예요|라고|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.strip())
        if match:
            return match.group(1).strip()
    return None


def recall_user_name(question: str, chat_history: List[Dict[str, Any]]) -> Optional[str]:
    current_name = extract_user_name(question)
    if current_name:
        return current_name
    for item in reversed(chat_history):
        if item.get("role") != "user":
            continue
        remembered = extract_user_name(str(item.get("content") or ""))
        if remembered:
            return remembered
    return None


def is_user_name_question(question: str) -> bool:
    normalized = " ".join((question or "").strip().split())
    return bool(re.search(r"(내|제)\s*이름.*(뭐|누구|기억|알)", normalized))


def make_session_title(plant: Dict[str, Any], question: str) -> str:
    plant_label = (plant.get("name") or plant.get("species") or "식물").strip()
    clean_question = " ".join((question or "").split())
    if len(clean_question) > 24:
        clean_question = clean_question[:24].rstrip() + "..."
    if not clean_question:
        clean_question = "상담"
    return f"{plant_label} · {clean_question}"

def chat_mode_prefix(response_mode: str) -> str:
    return "[내 식물]" if response_mode == "companion" else "[전문가]"

def make_mode_session_title(plant: Dict[str, Any], question: str, response_mode: str) -> str:
    return f"{chat_mode_prefix(response_mode)} {make_session_title(plant, question)}"

class AgentState(TypedDict):
    # 입력 정보
    db_client: Client
    user_id: str
    plant_id: str
    care_log_id: Optional[str]
    photo_id: Optional[str]
    question: str
    response_mode: str
    request_chat_history: List[Dict[str, Any]]
    chat_history: List[Dict[str, Any]]
    target_session_id: Optional[str]
    
    # 런타임 획득 정보
    plant_data: Dict[str, Any]
    care_logs: List[Dict[str, Any]]
    photo_data: Dict[str, Any]
    recent_photos: List[Dict[str, Any]]
    
    # 노드 결과물
    image_signals: List[str]
    image_description: str
    vision_error: Optional[str]
    user_context: str
    search_query: str
    retrieved_docs: List[Dict[str, Any]]
    draft_answer: Dict[str, Any]
    final_answer: Dict[str, Any]
    session_id: Optional[str]
    message_id: Optional[str]
    new_session: bool

# 1. validate_input 노드
def validate_input(state: AgentState) -> Dict[str, Any]:
    db = state["db_client"]
    plant_id = state["plant_id"]
    user_id = state["user_id"]
    
    plant_response = db.table("plants").select("*").eq("id", plant_id).eq("user_id", user_id).execute()
    if not plant_response.data:
        raise ValueError("식물을 찾을 수 없거나 해당 식물에 대한 접근 권한이 없습니다.")
    
    if state.get("care_log_id"):
        selected_log_res = (
            db.table("care_logs")
            .select("*")
            .eq("id", state["care_log_id"])
            .eq("plant_id", plant_id)
            .execute()
        )
        if not selected_log_res.data:
            raise ValueError("재배 일지를 찾을 수 없거나 해당 식물에 대한 접근 권한이 없습니다.")
        logs = selected_log_res.data
    else:
        logs_res = db.table("care_logs").select("*").eq("plant_id", plant_id).order("created_at", desc=True).limit(5).execute()
        logs = logs_res.data or []
    
    photo_data = {}
    if state.get("photo_id"):
        photo_res = db.table("plant_photos").select("*").eq("id", state["photo_id"]).eq("plant_id", plant_id).execute()
        if photo_res.data:
            photo_data = photo_res.data[0]

    recent_photos_res = db.table("plant_photos").select("*").eq("plant_id", plant_id).order("created_at", desc=True).limit(5).execute()

    return {
        "plant_data": plant_response.data[0],
        "care_logs": logs,
        "photo_data": photo_data,
        "recent_photos": recent_photos_res.data or []
    }

def load_chat_history(state: AgentState) -> Dict[str, Any]:
    db = state["db_client"]
    user_id = state["user_id"]
    plant_id = state["plant_id"]
    response_mode = state.get("response_mode") or "expert"
    prefix = chat_mode_prefix(response_mode)
    request_history = [
        {"role": item.get("role"), "content": str(item.get("content") or "")}
        for item in state.get("request_chat_history") or []
        if item.get("role") in {"user", "assistant"} and str(item.get("content") or "").strip()
    ]

    if state.get("new_session"):
        return {"chat_history": request_history[-12:], "session_id": None}

    try:
        target_session_id = state.get("target_session_id")
        if target_session_id:
            session_res = (
                db.table("chat_sessions")
                .select("id")
                .eq("id", target_session_id)
                .eq("user_id", user_id)
                .eq("plant_id", plant_id)
                .limit(1)
                .execute()
            )
            if not session_res.data:
                raise ValueError("상담 세션을 찾을 수 없거나 해당 세션에 대한 권한이 없습니다.")
        else:
            session_res = (
                db.table("chat_sessions")
                .select("id")
                .eq("user_id", user_id)
                .eq("plant_id", plant_id)
                .like("title", f"{prefix}%")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        if not session_res.data:
            return {"chat_history": request_history[-12:], "session_id": None}

        session_id = session_res.data[0]["id"]
        messages_res = (
            db.table("chat_messages")
            .select("role,sender,content,created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(12)
            .execute()
        )
        history = []
        for item in reversed(messages_res.data or []):
            content = item.get("content")
            if isinstance(content, dict):
                text = content.get("text", "")
                image_analysis = content.get("imageAnalysis")
                image_signals = content.get("imageSignals")
                if image_analysis:
                    text = f"{text}\n[이전에 첨부한 사진 분석: {image_analysis}]".strip()
                if image_signals:
                    text = f"{text}\n[이전 사진 관찰 신호: {', '.join(str(signal) for signal in image_signals)}]".strip()
            else:
                text = str(content or "")
            if text.strip():
                history.append({
                    "role": item.get("role") or item.get("sender") or "user",
                    "content": text.strip()
                })
        merged = [*history, *request_history]
        deduped = []
        seen = set()
        for item in merged:
            key = (item.get("role"), item.get("content"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return {"chat_history": deduped[-12:], "session_id": session_id}
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        logger.warning("Chat memory unavailable: %s", exc)
        return {"chat_history": request_history[-12:], "session_id": None}

# 2. extract_image_signals 노드
def extract_image_signals(state: AgentState) -> Dict[str, Any]:
    db = state["db_client"]
    photo = state.get("photo_data")
    logs = state.get("care_logs") or []
    question = state["question"].lower()
    signals = []
    image_description = ""
    vision_error: Optional[str] = None
    
    # 간단한 키워드 추출 (Fallback)
    if "노랗" in question or "황화" in question or "색이 바" in question:
        signals.append("잎 변색 (황화)")
    if "시들" in question or "말라" in question or "힘이 없" in question:
        signals.append("줄기/잎 시듦 및 탈수")
    if "반점" in question or "벌레" in question or "응애" in question:
        signals.append("병해충 의심 반점/흔적")
        
    # 이미지 설명이 있으면 추가
    if photo and photo.get("note"):
        signals.append(f"사용자 사진 메모: {photo['note']}")

    if photo and photo.get("storage_path"):
        try:
            analysis = analyze_plant_image(db, photo["storage_path"], state["question"])
            signals.extend(analysis.get("signals") or [])
            image_description = analysis.get("description") or ""
        except VisionAnalysisError as exc:
            vision_error = str(exc)
            logger.warning("Vision analysis skipped: %s", exc)

    for log in logs[:3]:
        for label, field in [("잎 상태", "leaf_condition"), ("흙 상태", "soil_condition"), ("재배 메모", "memo")]:
            value = log.get(field)
            if value:
                signals.append(f"최근 {label}: {value}")
        
    return {
        "image_signals": signals,
        "image_description": image_description,
        "vision_error": vision_error,
    }

# 3. summarize_user_context 노드
def summarize_user_context(state: AgentState) -> Dict[str, Any]:
    plant = state["plant_data"]
    logs = state["care_logs"]
    photo = state.get("photo_data") or {}
    
    context_parts = [
        f"식물 별명: {plant.get('name') or '알 수 없음'}",
        f"식물 품종: {plant.get('species') or '알 수 없음'}",
        f"키우는 위치: {plant.get('location') or '미지정'}",
        f"조도/햇빛: {plant.get('sunlight') or '미지정'}"
    ]

    if plant.get("health_score") is not None:
        context_parts.append(f"앱 건강 점수: {plant.get('health_score')}")
    if plant.get("moisture"):
        context_parts.append(f"앱 수분 상태: {plant.get('moisture')}")
    if plant.get("next_task"):
        context_parts.append(f"다음 관리 작업: {plant.get('next_task')}")
    
    if logs:
        for index, log in enumerate(logs[:3], start=1):
            log_parts = [
                f"#{index}",
                f"물 준 날짜={log.get('watered_at') or '기록 없음'}",
                f"잎={log.get('leaf_condition') or '기록 없음'}",
                f"흙={log.get('soil_condition') or '기록 없음'}",
                f"메모={log.get('memo') or '없음'}"
            ]
            context_parts.append("최근 재배 일지 " + ", ".join(log_parts))

    if photo:
        context_parts.append(
            f"상담 첨부 사진: 촬영일={photo.get('captured_at') or '미지정'}, 메모={photo.get('note') or '없음'}, 저장경로={photo.get('storage_path') or '없음'}"
        )
    return {"user_context": " / ".join(context_parts)}

# 4. build_retrieval_query 노드
def build_retrieval_query(state: AgentState) -> Dict[str, Any]:
    plant = state["plant_data"]
    question = state["question"]
    signals = ", ".join(state["image_signals"])
    context = state.get("user_context", "")
    image_description = state.get("image_description") or ""

    if is_smalltalk_question(question):
        return {"search_query": ""}
    
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    if openai_key:
        try:
            import json
            from openai import OpenAI
            client = OpenAI(api_key=openai_key, timeout=12.0, max_retries=0)
            prompt = (
                "당신은 식물 관리 RAG 시스템의 검색 쿼리 생성기입니다. "
                "주어진 상황에서 가장 관련성 높은 문서를 찾기 위한 검색 키워드 3개를 만드세요. "
                "JSON 형식으로 {'queries': ['키워드1', '키워드2', '키워드3']} 반환하세요."
            )
            res = client.chat.completions.create(
                model=os.getenv("CHAT_MODEL") or settings.CHAT_MODEL,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"질문: {question}\n식물: {plant.get('species') or plant.get('name')}\n징후: {signals}\n사진: {image_description}"}
                ]
            )
            raw_content = str(res.choices[0].message.content or "").strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            ans = json.loads(raw_content)
            queries = ans.get("queries") or []
            if queries:
                return {"search_query": " ".join(queries)}
        except Exception as e:
            logger.warning("Query expansion failed: %s", e)

    query_text = (
        f"식물: {plant.get('species') or plant.get('name')}. "
        f"사용자 질문: {question}. "
        f"관찰 징후: {signals}. "
        f"사진 분석: {image_description}. "
        f"관리 맥락: {context}"
    )
    return {"search_query": query_text}

# 5. retrieve_docs 노드
def retrieve_docs(state: AgentState) -> Dict[str, Any]:
    if is_smalltalk_question(state.get("question") or ""):
        return {"retrieved_docs": []}
    plant = state.get("plant_data") or {}
    question = state.get("question") or ""
    compact_query = " ".join(
        str(part)
        for part in [
            plant.get("name"),
            plant.get("species"),
            question,
            ", ".join(state.get("image_signals") or []),
            state.get("image_description") or "",
        ]
        if part
    )
    generated_query = state.get("search_query") or ""
    query_parts = [compact_query, generated_query]
    query = " ".join(dict.fromkeys(part.strip() for part in query_parts if part and part.strip()))
    if not query.strip():
        query = generated_query
    search_results = search_documents(query, top_k=8)
    
    docs = []
    for res in search_results:
        docs.append({
            "content": res.content,
            "metadata": res.metadata,
            "score": res.score
        })
    return {"retrieved_docs": docs}

# 6. grade_or_rerank 노드
def grade_or_rerank(state: AgentState) -> Dict[str, Any]:
    docs = state["retrieved_docs"]
    question = state["question"]
    plant = state.get("plant_data") or {}
    plant_label = " ".join(
        str(part).strip()
        for part in [plant.get("name"), plant.get("species")]
        if part
    ) or "unknown plant"
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    
    if not openai_key or not docs:
        return {"retrieved_docs": docs[:4]}
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key, timeout=12.0, max_retries=0)
        
        filtered_docs = []
        for doc in docs:
            res = client.chat.completions.create(
                model=os.getenv("CHAT_MODEL") or settings.CHAT_MODEL,
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 RAG 시스템의 문서 관련성 평가기입니다. 사용자의 질문에 답하기 위해 주어진 문서가 유용한지 판별합니다. "
                            "사용자가 특정 식물/작물에 대해 묻는 경우, 문서가 같은 식물/작물이거나 질문에 직접 도움이 되는 일반 관리 원칙을 담을 때만 'yes'를 출력하세요. "
                            "문서가 다른 식물/작물 전용이고 현재 질문과 무관하면 무조건 'no'를 출력하세요. "
                            "결과는 오직 'yes' 또는 'no'만 출력하세요."
                        )
                    },
                    {"role": "user", "content": f"식물/작물: {plant_label}\n질문: {question}\n\n문서 제목: {(doc.get('metadata') or {}).get('title')}\n문서 내용: {doc.get('content')}"}
                ]
            )
            score = str(res.choices[0].message.content or "").strip().lower()
            if 'yes' in score:
                filtered_docs.append(doc)
                if len(filtered_docs) >= 4:
                    break
                    
        # 필터링 후에도 문서가 없으면(모두 no인 경우) 원본 상위 2개라도 살림
        if not filtered_docs:
            filtered_docs = []
            
        return {"retrieved_docs": filtered_docs}
    except Exception as e:
        logger.warning("Reranking failed: %s", e)
        return {"retrieved_docs": docs[:4]}

# 7. generate_answer 노드
def generate_answer(state: AgentState) -> Dict[str, Any]:
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    docs = state["retrieved_docs"]
    question = state["question"]
    context = state["user_context"]
    image_description = state.get("image_description") or "사진 분석 결과 없음"
    vision_error = state.get("vision_error")
    response_mode = state.get("response_mode") or "expert"
    is_companion_mode = response_mode == "companion"
    plant = state.get("plant_data") or {}
    plant_label = plant.get("name") or plant.get("species") or "식물"
    chat_history = state.get("chat_history") or []
    history_text = "\n".join(
        f"{'사용자' if item.get('role') == 'user' else 'AI'}: {item.get('content')}"
        for item in chat_history[-8:]
    )
    remembered_name = recall_user_name(question, chat_history)

    if extract_user_name(question):
        if is_companion_mode:
            summary = f"알겠어. 네 이름은 {remembered_name}이야. 이 상담방에서는 그렇게 기억해둘게."
        else:
            summary = f"알겠습니다. 사용자님의 이름은 {remembered_name}입니다. 이 상담방에서 그렇게 기억해두겠습니다."
        return {
            "draft_answer": {
                "summary": summary,
                "possibleCauses": [],
                "todayActions": ["이 이름은 현재 상담방의 대화 맥락에서 이어서 참고합니다."],
                "observationChecklist": [],
                "citations": [],
            }
        }

    if is_user_name_question(question):
        if remembered_name:
            summary = f"네 이름은 {remembered_name}이야." if is_companion_mode else f"사용자님의 이름은 {remembered_name}입니다."
        else:
            summary = "아직 이 상담방에서 이름을 들은 기록을 찾지 못했어." if is_companion_mode else "아직 이 상담방에서 사용자님의 이름을 확인한 기록이 없습니다."
        return {
            "draft_answer": {
                "summary": summary,
                "possibleCauses": [],
                "todayActions": [],
                "observationChecklist": [],
                "citations": [],
            }
        }
    
    if is_smalltalk_question(question):
        if is_companion_mode:
            return {
                "draft_answer": {
                    "summary": f"안녕, 나 {plant_label}야. 오늘 내 잎이나 흙 상태가 궁금하면 편하게 물어봐. 사진도 같이 보내주면 내가 지금 어떤 느낌인지 더 잘 말해볼게.",
                    "possibleCauses": ["아직 구체적인 질문이나 상태 사진이 없어서 내 컨디션을 정확히 말하긴 어려워."],
                    "todayActions": ["오늘은 내 흙이 얼마나 말랐는지 한 번 만져봐 줘.", "빛이 너무 세거나 바람이 바로 닿는 곳은 아닌지도 봐줘."],
                    "observationChecklist": ["잎 색이 변했는지", "흙이 젖어 있는지", "마지막 물 준 날이 언제인지", "새잎이 잘 펴지는지"],
                    "citations": [],
                }
            }
        return {
            "draft_answer": {
                "summary": f"안녕하세요. {plant_label} 상담을 도와드릴게요. 물주기, 빛, 잎 상태, 흙 상태, 사진 진단 중 궁금한 내용을 편하게 적어주세요.",
                "possibleCauses": ["아직 구체적인 증상이나 관리 질문이 입력되지 않았습니다."],
                "todayActions": ["궁금한 점을 한 문장으로 적거나, 상태 사진을 첨부해 주세요."],
                "observationChecklist": ["잎 색 변화", "흙 마름 정도", "최근 물 준 날짜", "빛을 받는 시간"],
                "citations": [],
            }
        }

    citations = []
    seen_sources = set()
    for doc in docs:
        metadata = doc.get("metadata") or {}
        source_id = metadata.get("source_id") or metadata.get("sourceId") or "unknown"
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)
        citations.append({
            "sourceId": source_id,
            "title": metadata.get("title") or "출처 미상",
            "url": metadata.get("url"),
            "publisher": metadata.get("publisher"),
            "excerpt": make_excerpt(doc.get("content") or ""),
            "section": metadata.get("section") or metadata.get("category") or metadata.get("source_type")
        })
        
    if openai_key:
        try:
            import json
            from openai import OpenAI
            
            docs_text = "\n\n".join([
                f"--- 문서: {(d.get('metadata') or {}).get('title') or '출처 미상'} ---\n{d.get('content') or ''}"
                for d in docs
            ])
            mode_instruction = (
                f"답변 모드는 '내 식물과 대화하기'입니다. 당신은 사용자가 등록한 식물 '{plant_label}' 자신처럼 1인칭으로 말하세요. "
                "친근한 반말을 사용하되 유치하거나 과장하지 말고, 식물이 부탁하는 듯한 짧은 문장을 섞으세요. "
                "예: '나 내일 흙이 말라 있으면 물 한 번 부탁해.', '오늘은 빛이 너무 세지 않은지 봐줘.' "
                "possibleCauses도 '내가 힘든 이유 후보'처럼 자연스럽게 쓰고, todayActions는 사용자가 식물을 돌보는 행동으로 작성하세요. "
                "공식 문서 근거가 부족하면 '확실히는 모르겠어'라고 말하세요. 안전 관련 내용은 장난처럼 표현하지 마세요. "
            ) if is_companion_mode else (
                "답변 모드는 '전문가와 상담하기'입니다. 차분하고 전문적인 상담 말투를 사용하세요. "
                "summary는 한 문단의 자연스러운 상담 말투로 작성하고, todayActions는 사용자가 바로 따라 할 수 있는 구체적인 행동으로 작성하세요. "
            )

            client = OpenAI(api_key=openai_key, timeout=18.0, max_retries=0)
            res = client.chat.completions.create(
                model=os.getenv("CHAT_MODEL") or settings.CHAT_MODEL,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 식물 관리 상담을 돕는 AI입니다. 반드시 사용자의 식물 정보, 최근 관리 기록, 검색된 공식 문서만 근거로 답하세요. "
                            "모든 답변은 JSON 객체만 출력합니다. "
                            "필드: evidenceNotes(string), summary(string), possibleCauses(string[]), todayActions(string[]), observationChecklist(string[]). "
                            "evidenceNotes 필드에는 사용자에게 보여줄 수 있는 짧은 근거 요약만 작성하세요. 내부 추론 과정이나 생각의 흐름은 출력하지 마세요. "
                            f"{mode_instruction}"
                            "이전 대화 메모리는 사용자의 선호, 이름, 직전 맥락을 이해하는 보조 정보로만 사용하세요. "
                            "현재 질문과 무관한 이전 증상, 이전 문서, 이전 답변 근거를 새 답변에 끌어오지 마세요. "
                            "현재 검색된 공식 문서가 없으면 문서 근거가 없다고 명확히 말하세요. "
                            "질병명 확정, 농약 직접 처방, 과도한 단정은 피하고 '~가능성', '관찰 필요' 중심으로 말하세요. "
                            "사진 분석 결과가 있으면 이를 관찰 근거로 반영하되, 사진만으로 확정 진단하지 마세요. "
                            "검색 문서가 부족하면 부족하다고 말하고 추가 사진/물주기/빛/흙 상태 정보를 요청하세요. "
                            "답변 안에서 출처 번호를 직접 꾸며 쓰기보다, 근거 문서는 citations 영역으로 제공된다고 가정하세요."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"[식물 정보]\n{context}\n\n"
                            f"[사진 분석 결과]\n{image_description}\n\n"
                            f"[사진 분석 참고]\n{vision_error or '오류 없음'}\n\n"
                            f"[이전 대화 메모리]\n{history_text or '이전 대화 없음'}\n\n"
                            f"[검색된 공식 문서]\n{docs_text or '검색 문서 없음'}\n\n"
                            f"[사용자 질문]\n{question}"
                        )
                    }
                ]
            )

            raw_content = str(res.choices[0].message.content or "").strip()
            if raw_content.startswith("```"):
                raw_content = raw_content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            ans = json.loads(raw_content)
            return {
                "draft_answer": {
                    "summary": ans.get("summary") or "입력된 식물 상태와 공식 자료를 바탕으로 관리 가이드를 정리했습니다.",
                    "possibleCauses": ans.get("possibleCauses") or ["입력 정보만으로 확정하기 어려워 추가 관찰이 필요합니다."],
                    "todayActions": ans.get("todayActions") or ["흙 수분, 빛, 통풍 상태를 먼저 확인합니다."],
                    "observationChecklist": ans.get("observationChecklist") or ["잎 색 변화, 줄기 무름, 흙 냄새를 3~7일간 관찰합니다."],
                    "citations": citations
                }
            }
        except Exception as e:
            print(f"[RAG LLM WARNING] OpenAI 답변 생성 중 실패, 룰베이스 전환: {e}")
            
    combined_docs_text = " ".join([d.get("content", "") for d in docs])
    combined_signal_text = f"{question} {context} {image_description} {' '.join(state.get('image_signals') or [])} {combined_docs_text}".lower()

    if not docs:
        if is_companion_mode:
            summary = f"지금은 나({plant_label})에 대한 공식 문서 근거가 충분하지 않아서 확실히 말하긴 어려워. 그래도 오늘 내 잎, 흙, 빛 상태를 같이 보면 다음 답변은 훨씬 정확해질 거야."
            possible_causes = [
                "내 최근 물주기나 빛 기록이 부족해서 컨디션 원인을 좁히기 어려워.",
                "사진이나 재배 일지가 없으면 잎 변화가 일시적인지 관리 문제인지 헷갈릴 수 있어."
            ]
            today_actions = [
                "내 잎 앞뒤랑 흙 표면 사진을 한 장씩 남겨줘.",
                "마지막으로 물 준 날짜와 흙이 마르는 속도를 기록해줘."
            ]
            checklist = [
                "새잎까지 색 변화가 번지는지 봐줘.",
                "줄기 밑동이 무르거나 흙 냄새가 이상한지 확인해줘."
            ]
        else:
            summary = "현재 질문과 식물 기록만으로는 공식 문서 근거가 충분하지 않아 확정적인 판단은 어렵습니다."
            possible_causes = [
                "최근 물주기, 빛, 통풍, 흙 상태 정보가 부족합니다.",
                "사진이나 재배 일지 없이 증상만으로는 원인 후보를 좁히기 어렵습니다."
            ]
            today_actions = [
                "잎 앞뒤, 줄기 밑동, 흙 표면 사진을 추가로 기록합니다.",
                "최근 물 준 날짜와 흙이 마르는 속도를 재배 일지에 남깁니다."
            ]
            checklist = [
                "잎 색 변화가 새잎까지 번지는지 확인합니다.",
                "줄기 밑동이 무르거나 흙 냄새가 나는지 확인합니다."
            ]
    elif any(token in combined_signal_text for token in ["과습", "물주기", "젖", "축축", "무름", "뿌리"]):
        summary = "입력된 증상과 검색 문서를 보면 과습 또는 배수 불량 가능성을 우선 점검해야 합니다."
        possible_causes = [
            "배수가 잘 되지 않거나 흙이 마르기 전 잦은 관수",
            "화분 물받이에 고여있는 정체수"
        ]
        today_actions = [
            "화분 밑 물받이에 고인 물을 완전히 비워줍니다.",
            "손가락 두 마디 깊이까지 흙이 말랐는지 확인하고, 젖어 있으면 물주기를 미룹니다."
        ]
        checklist = [
            "새싹이나 안쪽 줄기가 무르거나 갈색으로 변하는지 3~7일간 관찰합니다.",
            "흙 냄새가 시큼하거나 곰팡이 냄새가 나는지 확인합니다."
        ]
    elif any(token in combined_signal_text for token in ["노랗", "황화", "색이", "하엽", "영양", "질소", "비료"]):
        summary = "잎 황화가 보인다면 과습, 광량 변화, 영양 부족 가능성을 함께 비교해야 합니다."
        possible_causes = [
            "오래된 하엽부터 노랗게 변하는 자연 노화 또는 영양 부족",
            "젖은 흙이 오래 유지되어 뿌리 기능이 떨어진 상태",
            "갑작스러운 빛 환경 변화"
        ]
        today_actions = [
            "새잎과 오래된 잎 중 어디부터 노랗게 변하는지 구분해 기록합니다.",
            "흙 수분을 먼저 확인하고, 젖어 있으면 비료보다 건조와 통풍을 우선합니다."
        ]
        checklist = [
            "노란 부위가 잎맥 사이인지, 잎 가장자리인지, 전체 잎인지 관찰합니다.",
            "다음 물주기 전까지 황화 범위가 넓어지는지 확인합니다."
        ]
    elif any(token in combined_signal_text for token in ["건조", "마름", "잎 끝", "갈변", "바삭", "습도"]):
        summary = "잎끝 마름이나 갈변은 건조, 강한 빛, 물 부족 스트레스 가능성이 있습니다."
        possible_causes = [
            "난방기구 주변이나 바람이 직접 닿아 일어난 습도 저하",
            "흙 하부까지 충분히 젖지 않는 얕은 관수",
            "강한 직사광선 또는 급격한 위치 변화"
        ]
        today_actions = [
            "화분 무게와 흙 속 수분을 확인한 뒤 말랐다면 배수구로 물이 빠질 만큼 충분히 관수합니다.",
            "난방기, 에어컨, 강한 직사광선 위치에서 한 발 떨어뜨립니다."
        ]
        checklist = [
            "잎끝 마름이 멈추는지, 새잎에도 반복되는지 관찰합니다.",
            "실내 습도가 40% 이하로 오래 유지되는지 확인합니다."
        ]
    elif any(token in combined_signal_text for token in ["벌레", "응애", "깍지", "진딧", "반점", "해충"]):
        summary = "반점이나 해충 흔적이 있다면 병해충 가능성을 배제하지 말고 잎 뒷면을 확인해야 합니다."
        possible_causes = [
            "잎 뒷면이나 줄기 마디에 붙은 소형 해충",
            "통풍 부족과 과습이 겹친 반점성 이상",
            "물방울 또는 강한 빛에 의한 국소 손상"
        ]
        today_actions = [
            "잎 뒷면, 줄기 마디, 새순 주변을 확대해서 확인하고 사진으로 남깁니다.",
            "해당 식물을 다른 식물과 잠시 떨어뜨려 관찰합니다."
        ]
        checklist = [
            "흰 가루, 거미줄, 끈적임, 작은 점이 움직이는지 확인합니다.",
            "반점이 원형으로 커지거나 주변 잎으로 번지는지 관찰합니다."
        ]
    else:
        summary = "검색된 공식 자료와 식물 기록을 기준으로 기본 관리 상태를 점검해야 합니다."
        possible_causes = [
            "물주기, 광량, 통풍 중 하나가 현재 식물 조건과 맞지 않을 가능성",
            "최근 위치 변경이나 계절 변화에 따른 일시적 적응 반응"
        ]
        today_actions = [
            "흙 수분, 빛이 닿는 시간, 통풍 상태를 오늘 기준으로 기록합니다.",
            "증상이 보이는 잎과 정상 잎을 함께 촬영해 비교 기록을 남깁니다."
        ]
        checklist = [
            "3~7일 동안 증상이 새잎으로 확산되는지 확인합니다.",
            "물주기 후 회복되는지 또는 더 처지는지 관찰합니다."
        ]

    if is_companion_mode and not summary.startswith("지금은 나("):
        summary = f"나({plant_label}) 상태를 보면, {summary.replace('입니다.', '인 것 같아.').replace('합니다.', '해줘.')}"
        possible_causes = [item.replace("가능성", "가능성이 있어").replace("상태", "상태일 수 있어") for item in possible_causes]
        today_actions = [
            item.replace("확인합니다.", "확인해줘.").replace("기록합니다.", "기록해줘.").replace("남깁니다.", "남겨줘.").replace("미룹니다.", "미뤄줘.")
            for item in today_actions
        ]
        checklist = [
            item.replace("확인합니다.", "확인해줘.").replace("관찰합니다.", "관찰해줘.").replace("기록합니다.", "기록해줘.")
            for item in checklist
        ]
        
    return {
        "draft_answer": {
            "summary": summary,
            "possibleCauses": possible_causes,
            "todayActions": today_actions,
            "observationChecklist": checklist,
            "citations": citations
        }
    }

# 8. safety_review 노드
def safety_review(state: AgentState) -> Dict[str, Any]:
    draft = state["draft_answer"]
    response_mode = state.get("response_mode") or "expert"
    
    if response_mode == "companion":
        safety_notice = "친근한 대화 모드의 답변이지만, 실제 관리는 입력된 내용과 공식 지침서에 기반한 참고 가이드입니다. 증상이 지속되면 전문가 확인을 권장합니다."
    else:
        safety_notice = "본 관리 가이드는 입력된 내용 및 공식 지침서에 기반하여 생성되었으며 특정 질병을 확정하는 것이 아닙니다. 상세 증상이 지속되면 농업기술센터 전문가의 도움을 받으십시오."
    
    today_actions = []
    for act in draft["todayActions"]:
        if "농약" in act or "살충" in act:
            today_actions.append(f"{act} (안전사용기준 준수 및 전문가 상담 권장)")
        else:
            today_actions.append(act)
            
    final_answer = {
        "summary": draft["summary"],
        "possibleCauses": draft["possibleCauses"],
        "todayActions": today_actions,
        "observationChecklist": draft["observationChecklist"],
        "citations": draft["citations"],
        "safetyNotice": safety_notice
    }
    return {"final_answer": final_answer}

# 9. persist_result 노드 (DB 영속화)
def persist_result(state: AgentState) -> Dict[str, Any]:
    db = state["db_client"]
    user_id = state["user_id"]
    plant_id = state["plant_id"]
    final = state["final_answer"]
    question = state["question"]
    response_mode = state.get("response_mode") or "expert"
    prefix = chat_mode_prefix(response_mode)

    try:
        session_res = None
        session_id = state.get("session_id")
        if session_id and not state.get("new_session"):
            try:
                existing = db.table("chat_sessions").select("title").eq("id", session_id).eq("user_id", user_id).limit(1).execute()
                if existing.data and not existing.data[0].get("title"):
                    db.table("chat_sessions").update({"title": make_mode_session_title(state["plant_data"], question, response_mode)}).eq("id", session_id).execute()
            except Exception:
                pass
        elif not state.get("new_session"):
            session_res = (
                db.table("chat_sessions")
                .select("id,title")
                .eq("user_id", user_id)
                .eq("plant_id", plant_id)
                .like("title", f"{prefix}%")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

        if session_id:
            pass
        elif session_res and session_res.data:
            session_id = session_res.data[0]["id"]
            if not session_res.data[0].get("title"):
                try:
                    db.table("chat_sessions").update({"title": make_mode_session_title(state["plant_data"], question, response_mode)}).eq("id", session_id).execute()
                except Exception:
                    pass
        else:
            new_session = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "plant_id": plant_id,
                "title": make_mode_session_title(state["plant_data"], question, response_mode)
            }
            db.table("chat_sessions").insert(new_session).execute()
            session_id = new_session["id"]

        user_msg_id = str(uuid.uuid4())
        user_content: Dict[str, Any] = {"text": question}
        if state.get("photo_id"):
            user_content["photoId"] = state.get("photo_id")
        if state.get("image_description"):
            user_content["imageAnalysis"] = state.get("image_description")
        if state.get("image_signals"):
            user_content["imageSignals"] = state.get("image_signals")
        user_message_payload = {
            "id": user_msg_id,
            "session_id": session_id,
            "role": "user",
            "content": user_content,
            "citations": []
        }
        try:
            db.table("chat_messages").insert(user_message_payload).execute()
        except Exception:
            db.table("chat_messages").insert({
                "id": user_msg_id,
                "session_id": session_id,
                "sender": "user",
                "content": question,
                "citations": []
            }).execute()

        ai_msg_id = str(uuid.uuid4())
        content_text = f"[요약]\n{final['summary']}\n\n[의심 원인]\n" + "\n".join(final['possibleCauses']) + "\n\n[오늘 할 일]\n" + "\n".join(final['todayActions'])

        db_citations = []
        for cit in final["citations"]:
            db_citations.append({
                "source_id": cit["sourceId"],
                "title": cit["title"],
                "url": cit["url"],
                "publisher": cit["publisher"],
                "excerpt": cit.get("excerpt"),
                "section": cit.get("section")
            })

        assistant_message_payload = {
            "id": ai_msg_id,
            "session_id": session_id,
            "role": "assistant",
            "content": {"text": content_text},
            "citations": db_citations
        }
        try:
            db.table("chat_messages").insert(assistant_message_payload).execute()
        except Exception:
            db.table("chat_messages").insert({
                "id": ai_msg_id,
                "session_id": session_id,
                "sender": "assistant",
                "content": content_text,
                "citations": db_citations
            }).execute()

        return {
            "session_id": session_id,
            "message_id": ai_msg_id
        }
    except Exception as exc:
        logger.warning("Chat persistence skipped after answer generation: %s", exc)
        return {
            "session_id": None,
            "message_id": None
        }

def run_rag_workflow(
    db_client: Client,
    user_id: str,
    plant_id: str,
    care_log_id: Optional[str],
    photo_id: Optional[str],
    question: str,
    new_session: bool = False,
    response_mode: str = "expert",
    recent_messages: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("load_chat_history", load_chat_history)
    workflow.add_node("extract_image_signals", extract_image_signals)
    workflow.add_node("summarize_user_context", summarize_user_context)
    workflow.add_node("build_retrieval_query", build_retrieval_query)
    workflow.add_node("retrieve_docs", retrieve_docs)
    workflow.add_node("grade_or_rerank", grade_or_rerank)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("safety_review", safety_review)
    workflow.add_node("persist_result", persist_result)
    
    workflow.set_entry_point("validate_input")
    workflow.add_edge("validate_input", "load_chat_history")
    workflow.add_edge("load_chat_history", "extract_image_signals")
    workflow.add_edge("extract_image_signals", "summarize_user_context")
    workflow.add_edge("summarize_user_context", "build_retrieval_query")
    workflow.add_edge("build_retrieval_query", "retrieve_docs")
    workflow.add_edge("retrieve_docs", "grade_or_rerank")
    workflow.add_edge("grade_or_rerank", "generate_answer")
    workflow.add_edge("generate_answer", "safety_review")
    workflow.add_edge("safety_review", "persist_result")
    workflow.add_edge("persist_result", END)
    
    app = workflow.compile()
    
    initial_state = {
        "db_client": db_client,
        "user_id": user_id,
        "plant_id": plant_id,
        "care_log_id": care_log_id,
        "photo_id": photo_id,
        "question": question,
        "response_mode": response_mode if response_mode in {"expert", "companion"} else "expert",
        "request_chat_history": recent_messages or [],
        "new_session": new_session,
        "target_session_id": session_id
    }
    
    result = app.invoke(initial_state)
    final_answer = dict(result["final_answer"])
    final_answer["sessionId"] = result.get("session_id")
    final_answer["messageId"] = result.get("message_id")
    return final_answer
