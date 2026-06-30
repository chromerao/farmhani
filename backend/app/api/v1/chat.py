import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, status, Depends, HTTPException, Path
from supabase import Client
from app.auth.security import get_current_user
from app.db.session import get_supabase_client
from app.schemas.chat import PlantCareChatRequest, PlantCareChatResponse, Citation, ChatSession, ChatMessage
from app.services.rag.pipeline import run_rag_workflow

router = APIRouter(prefix="/chat", tags=["Plant Care RAG Chat"])

@router.post("/plant-care", response_model=PlantCareChatResponse, status_code=status.HTTP_200_OK, summary="식물 케어 RAG 상담 실행")
async def consult_plant_care(
    request: PlantCareChatRequest,
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    """
    제공된 식물 ID, 최근 재배 일지, 업로드 사진을 기반으로 공공 원예 문서 RAG 모델을 구동하여 상태 진단 및 처방 가이드를 반환합니다.
    """
    try:
        final_answer = run_rag_workflow(
            db_client=db,
            user_id=str(current_user_id),
            plant_id=str(request.plantId),
            care_log_id=str(request.careLogId) if request.careLogId else None,
            photo_id=str(request.photoId) if request.photoId else None,
            question=request.question
        )
        
        citations = []
        for cit in final_answer["citations"]:
            citations.append(Citation(
                sourceId=cit["sourceId"],
                title=cit["title"],
                url=cit.get("url"),
                publisher=cit.get("publisher")
            ))
            
        return PlantCareChatResponse(
            summary=final_answer["summary"],
            possibleCauses=final_answer["possibleCauses"],
            todayActions=final_answer["todayActions"],
            observationChecklist=final_answer["observationChecklist"],
            citations=citations,
            safetyNotice=final_answer.get("safetyNotice")
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"식물 상담 RAG 수행 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/sessions", response_model=List[ChatSession], summary="상담 세션 목록 조회")
async def list_chat_sessions(
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    try:
        response = db.table("chat_sessions").select("*").eq("user_id", str(current_user_id)).order("created_at", desc=True).execute()
        sessions = []
        for item in response.data:
            sessions.append(ChatSession(
                id=uuid.UUID(item["id"]),
                userId=uuid.UUID(item["user_id"]),
                plantId=uuid.UUID(item["plant_id"]) if item.get("plant_id") else None,
                createdAt=datetime.fromisoformat(item["created_at"])
            ))
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상담 세션 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/sessions/{sessionId}/messages", response_model=List[ChatMessage], summary="세션별 대화 메시지 이력 조회")
async def list_chat_messages(
    sessionId: uuid.UUID = Path(..., description="세션 UUID"),
    current_user_id: uuid.UUID = Depends(get_current_user),
    db: Client = Depends(get_supabase_client)
):
    try:
        session_check = db.table("chat_sessions").select("user_id").eq("id", str(sessionId)).execute()
        if not session_check.data or session_check.data[0]["user_id"] != str(current_user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="상담 세션을 찾을 수 없거나 해당 세션에 대한 권한이 없습니다."
            )
            
        response = db.table("chat_messages").select("*").eq("session_id", str(sessionId)).order("created_at", desc=False).execute()
        messages = []
        for item in response.data:
            citations_data = item.get("citations") or []
            citations = []
            for cit in citations_data:
                citations.append(Citation(
                    sourceId=cit.get("sourceId") or cit.get("source_id"),
                    title=cit.get("title"),
                    url=cit.get("url"),
                    publisher=cit.get("publisher")
                ))
                
            db_content = item.get("content")
            content_text = ""
            if isinstance(db_content, dict):
                content_text = db_content.get("text", "")
            else:
                content_text = str(db_content) if db_content is not None else ""

            messages.append(ChatMessage(
                id=uuid.UUID(item["id"]),
                sessionId=uuid.UUID(item["session_id"]),
                sender=item.get("role") or item.get("sender") or "user",
                content=content_text,
                citations=citations,
                createdAt=datetime.fromisoformat(item["created_at"])
            ))
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 메시지 조회 중 오류가 발생했습니다: {str(e)}"
        )
