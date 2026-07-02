from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.schemas.care_log import CareLog

class PlantCreate(BaseModel):
    name: str = Field(..., description="식물의 이름")
    species: Optional[str] = Field(None, description="식물의 종류")
    location: Optional[str] = Field(None, json_schema_extra={"example": "베란다"}, description="식물이 위치한 공간")
    sunlight: Optional[str] = Field(None, json_schema_extra={"example": "오전 직사광선"}, description="식물이 받는 햇빛의 종류/양")
    imageUrl: Optional[str] = Field(None, description="식물 대표 이미지 URL")

class Plant(PlantCreate):
    id: UUID
    createdAt: datetime

class PlantUpdate(BaseModel):
    name: Optional[str] = Field(None, description="식물의 새 별명")
    species: Optional[str] = Field(None, description="식물의 새 품종명")
    location: Optional[str] = Field(None, description="식물의 새 위치")
    sunlight: Optional[str] = Field(None, description="식물의 새 햇빛 환경")
    imageUrl: Optional[str] = Field(None, description="식물의 새 대표 이미지 URL")

class PlantPhotoCreate(BaseModel):
    storagePath: str = Field(..., description="Supabase Storage나 R2에 저장된 파일 경로")
    capturedAt: Optional[datetime] = Field(None, description="사진 촬영 시간")
    note: Optional[str] = Field(None, description="사진에 대한 메모/메모")

class PlantPhoto(PlantPhotoCreate):
    id: UUID
    plantId: UUID
    createdAt: datetime

class PlantDetail(Plant):
    careLogs: List[CareLog] = Field(default_factory=list, description="식물 재배 일지 목록")
    photos: List[PlantPhoto] = Field(default_factory=list, description="식물 사진 히스토리 목록")
