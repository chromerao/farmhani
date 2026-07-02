import os
import uuid
import logging
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


def make_session_title(plant: Dict[str, Any], question: str) -> str:
    plant_label = (plant.get("name") or plant.get("species") or "식물").strip()
    clean_question = " ".join((question or "").split())
    if len(clean_question) > 24:
        clean_question = clean_question[:24].rstrip() + "..."
    if not clean_question:
        clean_question = "상담"
    return f"{plant_label} · {clean_question}"

class AgentState(TypedDict):
    # 입력 정보
    db_client: Client
    user_id: str
    plant_id: str
    care_log_id: Optional[str]
    photo_id: Optional[str]
    question: str
    
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
            client = OpenAI(api_key=openai_key)
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
    query = compact_query or state["search_query"]
    if not query.strip():
        query = state["search_query"]
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
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    
    if not openai_key or not docs:
        return {"retrieved_docs": docs[:4]}
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        
        filtered_docs = []
        for doc in docs:
            res = client.chat.completions.create(
                model=os.getenv("CHAT_MODEL") or settings.CHAT_MODEL,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "사용자의 식물 관리 질문에 답하기 위해 주어진 문서가 유용한가요? 관련성이 있다면 'yes', 전혀 무관하다면 'no'만 출력하세요."},
                    {"role": "user", "content": f"질문: {question}\n\n문서 내용: {doc.get('content')}"}
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
    
    if is_smalltalk_question(question):
        plant = state.get("plant_data") or {}
        plant_label = plant.get("name") or plant.get("species") or "식물"
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

            client = OpenAI(api_key=openai_key)
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
                            "summary는 한 문단의 자연스러운 상담 말투로 작성하고, todayActions는 사용자가 바로 따라 할 수 있는 구체적인 행동으로 작성하세요. "
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
    
    session_res = None
    if not state.get("new_session"):
        session_res = db.table("chat_sessions").select("id,title").eq("user_id", user_id).eq("plant_id", plant_id).order("created_at", desc=True).limit(1).execute()
    
    if session_res and session_res.data:
        session_id = session_res.data[0]["id"]
        if not session_res.data[0].get("title"):
            try:
                db.table("chat_sessions").update({"title": make_session_title(state["plant_data"], question)}).eq("id", session_id).execute()
            except Exception:
                pass
    else:
        new_session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "plant_id": plant_id,
            "title": make_session_title(state["plant_data"], question)
        }
        db.table("chat_sessions").insert(new_session).execute()
        session_id = new_session["id"]
        
    user_msg_id = str(uuid.uuid4())
    user_message_payload = {
        "id": user_msg_id,
        "session_id": session_id,
        "role": "user",
        "content": {"text": question},
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

def run_rag_workflow(
    db_client: Client,
    user_id: str,
    plant_id: str,
    care_log_id: Optional[str],
    photo_id: Optional[str],
    question: str,
    new_session: bool = False
) -> Dict[str, Any]:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("extract_image_signals", extract_image_signals)
    workflow.add_node("summarize_user_context", summarize_user_context)
    workflow.add_node("build_retrieval_query", build_retrieval_query)
    workflow.add_node("retrieve_docs", retrieve_docs)
    workflow.add_node("grade_or_rerank", grade_or_rerank)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("safety_review", safety_review)
    workflow.add_node("persist_result", persist_result)
    
    workflow.set_entry_point("validate_input")
    workflow.add_edge("validate_input", "extract_image_signals")
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
        "new_session": new_session
    }
    
    result = app.invoke(initial_state)
    final_answer = dict(result["final_answer"])
    final_answer["sessionId"] = result.get("session_id")
    final_answer["messageId"] = result.get("message_id")
    return final_answer
