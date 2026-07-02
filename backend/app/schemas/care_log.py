from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from uuid import UUID

class CareLogCreate(BaseModel):
    wateredAt: Optional[date] = Field(None, description="마지막 물 준 날짜")
    leafCondition: Optional[str] = Field(None, description="잎의 상태 설명")
    soilCondition: Optional[str] = Field(None, description="흙의 상태 설명")
    memo: Optional[str] = Field(None, description="기타 재배 일지 내용")

class CareLog(CareLogCreate):
    id: UUID
    plantId: UUID
    createdAt: datetime

class CareLogUpdate(BaseModel):
    wateredAt: Optional[date] = Field(None, description="마지막 물 준 날짜")
    leafCondition: Optional[str] = Field(None, description="잎의 상태 설명")
    soilCondition: Optional[str] = Field(None, description="흙의 상태 설명")
    memo: Optional[str] = Field(None, description="기타 재배 일지 내용")
