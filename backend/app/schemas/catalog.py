from pydantic import BaseModel, Field
from typing import Optional

class PlantCatalogItem(BaseModel):
    id: str = Field(..., description="품종 고유 ID")
    name: str = Field(..., description="국문 식물 품종명 (예: 몬스테라 델리시오사)")
    species: str = Field(..., description="학명/영문 품종명 (예: Monstera deliciosa)")
    familyName: Optional[str] = Field(None, description="식물 과 이름 (예: 천남성과)")
    description: Optional[str] = Field(None, description="품종에 대한 특징 요약 설명")
