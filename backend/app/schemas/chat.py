from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class Citation(BaseModel):
    sourceId: str = Field(..., description="문서 출처 식별자")
    title: str = Field(..., description="출처 문서의 제목")
    url: Optional[str] = Field(None, description="출처 문서의 URL 링크")
    publisher: Optional[str] = Field(None, description="문서 발행 기관 (예: 국립원예특작과학원)")
    excerpt: Optional[str] = Field(None, description="답변 근거가 된 문서 발췌문")
    section: Optional[str] = Field(None, description="문서 내 위치나 섹션 설명")

class PlantCareChatRequest(BaseModel):
    plantId: UUID = Field(..., description="상담 대상 식물의 UUID")
    careLogId: Optional[UUID] = Field(None, description="참조할 재배 일지의 UUID")
    photoId: Optional[UUID] = Field(None, description="참조할 식물 사진의 UUID")
    newSession: bool = Field(False, description="기존 식물 상담 세션을 재사용하지 않고 새 상담방을 생성할지 여부")
    question: str = Field(..., json_schema_extra={"example": "잎 끝이 마르고 아래쪽 잎이 노랗게 변했어요."}, description="사용자가 AI에 묻는 질문")

class PlantCareChatResponse(BaseModel):
    summary: str = Field(..., description="식물의 현재 상태 및 증상 요약")
    possibleCauses: List[str] = Field(..., description="의심되는 원인 후보 리스트")
    todayActions: List[str] = Field(..., description="오늘 즉시 수행해야 할 관리 행동 리스트")
    observationChecklist: List[str] = Field(..., description="향후 추가적으로 관찰해야 할 포인트 리스트")
    citations: List[Citation] = Field(..., description="상담 답변의 근거가 된 공식 원예 자료 출처 목록")
    safetyNotice: Optional[str] = Field(None, description="확정 진단 불가 및 주의 사항 등 안전성 공지 문구")
    sessionId: Optional[UUID] = Field(None, description="저장된 상담 세션 UUID")
    messageId: Optional[UUID] = Field(None, description="저장된 assistant 메시지 UUID")

class ChatSession(BaseModel):
    id: UUID
    userId: UUID
    plantId: Optional[UUID] = None
    createdAt: datetime

class ChatMessage(BaseModel):
    id: UUID
    sessionId: UUID
    sender: str
    content: str
    citations: Optional[List[Citation]] = []
    createdAt: datetime
