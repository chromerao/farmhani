import os
import uuid
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, date, timezone
from supabase import Client

from app.services.rag.vectorstore import search_documents
from langgraph.graph import StateGraph, END

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
    
    # 노드 결과물
    image_signals: List[str]
    user_context: str
    search_query: str
    retrieved_docs: List[Dict[str, Any]]
    draft_answer: Dict[str, Any]
    final_answer: Dict[str, Any]
    session_id: Optional[str]
    message_id: Optional[str]

# 1. validate_input 노드
def validate_input(state: AgentState) -> Dict[str, Any]:
    db = state["db_client"]
    plant_id = state["plant_id"]
    user_id = state["user_id"]
    
    plant_response = db.table("plants").select("*").eq("id", plant_id).eq("user_id", user_id).execute()
    if not plant_response.data:
        raise ValueError("식물을 찾을 수 없거나 해당 식물에 대한 접근 권한이 없습니다.")
    
    # 이력 데이터 조회
    logs_res = db.table("care_logs").select("*").eq("plant_id", plant_id).order("created_at", desc=True).limit(3).execute()
    
    photo_data = {}
    if state.get("photo_id"):
        photo_res = db.table("plant_photos").select("*").eq("id", state["photo_id"]).eq("plant_id", plant_id).execute()
        if photo_res.data:
            photo_data = photo_res.data[0]
            
    return {
        "plant_data": plant_response.data[0],
        "care_logs": logs_res.data or [],
        "photo_data": photo_data
    }

# 2. extract_image_signals 노드
def extract_image_signals(state: AgentState) -> Dict[str, Any]:
    photo = state.get("photo_data")
    question = state["question"].lower()
    signals = []
    
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
        
    return {"image_signals": signals}

# 3. summarize_user_context 노드
def summarize_user_context(state: AgentState) -> Dict[str, Any]:
    plant = state["plant_data"]
    logs = state["care_logs"]
    
    context_parts = [
        f"식물 별명: {plant['name']}",
        f"식물 품종: {plant.get('species') or '알 수 없음'}",
        f"키우는 위치: {plant.get('location') or '미지정'}",
        f"조도/햇빛: {plant.get('sunlight') or '미지정'}"
    ]
    
    if logs:
        last_watered = logs[0].get("watered_at") or "기록 없음"
        context_parts.append(f"최근 물 준 날짜: {last_watered}")
        context_parts.append(f"최근 잎 상태: {logs[0].get('leaf_condition') or '기록 없음'}")
        context_parts.append(f"최근 흙 상태: {logs[0].get('soil_condition') or '기록 없음'}")
        
    return {"user_context": " / ".join(context_parts)}

# 4. build_retrieval_query 노드
def build_retrieval_query(state: AgentState) -> Dict[str, Any]:
    plant = state["plant_data"]
    question = state["question"]
    signals = ", ".join(state["image_signals"])
    
    query_text = f"식물: {plant.get('species') or plant['name']}. 증상: {question}. 관찰 징후: {signals}"
    return {"search_query": query_text}

# 5. retrieve_docs 노드
def retrieve_docs(state: AgentState) -> Dict[str, Any]:
    query = state["search_query"]
    search_results = search_documents(query, top_k=2)
    
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
    return {"retrieved_docs": docs}

# 7. generate_answer 노드
def generate_answer(state: AgentState) -> Dict[str, Any]:
    openai_key = os.getenv("OPENAI_API_KEY")
    docs = state["retrieved_docs"]
    question = state["question"]
    context = state["user_context"]
    
    citations = []
    for doc in docs:
        citations.append({
            "sourceId": doc["metadata"]["source_id"],
            "title": doc["metadata"]["title"],
            "url": doc["metadata"]["url"],
            "publisher": doc["metadata"]["publisher"]
        })
        
    if openai_key:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            import json
            
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
            prompt = ChatPromptTemplate.from_messages([
                ("system", 
                 "당신은 전문 식물 주치의입니다. 아래 제공된 [식물 정보]와 [공식 가이드 문서]들을 기반으로 사용자의 질문에 답변을 생성해야 합니다.\n"
                 "답변은 반드시 아래 지정을 준수한 JSON 포맷이어야 합니다.\n\n"
                 "출력 JSON 스펙:\n"
                 "{{\n"
                 "  \"summary\": \"식물의 현재 상태 및 증상 요약\",\n"
                 "  \"possibleCauses\": [\"의심 원인 1\", \"의심 원인 2\"],\n"
                 "  \"todayActions\": [\"오늘 할 일 1\", \"오늘 할 일 2\"],\n"
                 "  \"observationChecklist\": [\"앞으로 관찰할 항목 1\", \"관찰할 항목 2\"]\n"
                 "}}\n\n"
                 "주의사항:\n"
                 "- 질병명 등을 확정하지 말고 '의심됩니다' 혹은 '~가능성이 있습니다' 등으로 표현하세요.\n"
                 "- 농약 정보 언급 시에는 안전사용기준 준수 및 전문가 상담 요망을 함께 작성하세요.\n\n"
                 "[식물 정보]\n{context}\n\n"
                 "[공식 가이드 문서]\n{docs_text}"),
                ("human", "{question}")
            ])
            
            docs_text = "\n\n".join([f"--- 문서: {d['metadata']['title']} ---\n{d['content']}" for d in docs])
            chain = prompt | llm
            res = chain.invoke({"context": context, "docs_text": docs_text, "question": question})
            
            ans = json.loads(res.content)
            return {
                "draft_answer": {
                    "summary": ans["summary"],
                    "possibleCauses": ans["possibleCauses"],
                    "todayActions": ans["todayActions"],
                    "observationChecklist": ans["observationChecklist"],
                    "citations": citations
                }
            }
        except Exception as e:
            print(f"[RAG LLM WARNING] OpenAI 답변 생성 중 실패, 룰베이스 전환: {e}")
            
    # Fallback 규칙 기반 템플릿 답변
    summary = "식물 관리 상태 분석 및 보완 가이드 제공"
    possible_causes = ["일시적인 실내 환경 적응 반응", "배수 상태 저하로 인한 산소 부족 의심"]
    today_actions = ["밝고 바람이 통하는 곳으로 식물을 이동시킵니다."]
    checklist = ["앞으로 7일 동안 잎의 생기와 무름 상태를 매일 관찰합니다."]
    
    combined_docs_text = "".join([d["content"] for d in docs])
    
    if "과습" in combined_docs_text or "물주기" in combined_docs_text:
        summary = "과습으로 인한 뿌리 산소 호흡 장애 및 잎 무름 의심"
        possible_causes = [
            "배수가 잘 되지 않거나 흙이 마르기 전 잦은 관수",
            "화분 물받이에 고여있는 정체수"
        ]
        today_actions = [
            "화분 밑 물받이에 고인 물을 완전히 비워줍니다.",
            "손가락 두 마디 깊이까지 흙이 완전히 말랐는지 확인한 후에만 다음 물을 줍니다."
        ]
        checklist = [
            "새로 나오는 새싹이나 안쪽 줄기가 무르고 갈색으로 썩어 들어가는지 매일 관찰하십시오."
        ]
    elif "양분" in combined_docs_text or "질소" in combined_docs_text:
        summary = "토양 영양소(특히 질소 성분) 결핍으로 인한 생리장해 의심"
        possible_causes = [
            "6개월 이상의 장기 재배로 인한 토양 미네랄 및 영양 고갈",
            "잘못된 비율의 분갈이 흙 배합"
        ]
        today_actions = [
            "물주기 시 적용 가능한 액체 비료를 매우 정밀하게 권장 배율로 희석하여 공급하십시오.",
            "가능하다면 새 흙으로 분갈이를 준비해 주십시오."
        ]
        checklist = [
            "비료 살포 후 아랫 잎 외에 윗 부분 잎의 녹색도가 돌아오는지 모니터링하십시오."
        ]
    elif "건조" in combined_docs_text or "잎 끝" in combined_docs_text:
        summary = "극심한 실내 건조로 인한 잎끝 탈수 현상 의심"
        possible_causes = [
            "난방기구 주변이나 바람이 직접 닿아 일어난 습도 저하",
            "낮은 상대 습도 (40% 이하)"
        ]
        today_actions = [
            "가습기를 가동하거나 식물 주변 잎에 가벼운 공중 분무를 주 2~3회 수행하십시오.",
            "난방기나 온풍기의 열기 배출구로부터 멀리 이동하십시오."
        ]
        checklist = [
            "잎 끝 마름 현상이 더 이상 잎 안쪽 안면부로 번지지 않고 멈추는지 관찰하십시오."
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
    
    session_res = db.table("chat_sessions").select("id").eq("user_id", user_id).eq("plant_id", plant_id).order("created_at", desc=True).limit(1).execute()
    
    if session_res.data:
        session_id = session_res.data[0]["id"]
    else:
        new_session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "plant_id": plant_id
        }
        db.table("chat_sessions").insert(new_session).execute()
        session_id = new_session["id"]
        
    user_msg_id = str(uuid.uuid4())
    db.table("chat_messages").insert({
        "id": user_msg_id,
        "session_id": session_id,
        "role": "user",
        "content": {"text": question},
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
            "publisher": cit["publisher"]
        })
        
    db.table("chat_messages").insert({
        "id": ai_msg_id,
        "session_id": session_id,
        "role": "assistant",
        "content": {"text": content_text},
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
    question: str
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
        "question": question
    }
    
    result = app.invoke(initial_state)
    return result["final_answer"]
