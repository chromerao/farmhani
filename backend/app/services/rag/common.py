"""RAG 파이프라인 공용 헬퍼 및 상태 정의."""
import re
from typing import Dict, Any, List, Optional, TypedDict

from supabase import Client


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
