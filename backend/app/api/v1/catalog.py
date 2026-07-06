import logging
from fastapi import APIRouter, Query, status, HTTPException
from typing import List, Optional
from app.schemas.catalog import PlantCatalogItem
from app.db import session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plant-catalog", tags=["Plant Catalog"])

def clean_search_term(value: str) -> str:
    return value.strip().replace("%", "").replace(",", " ").replace("(", " ").replace(")", " ")

@router.get("", response_model=List[PlantCatalogItem], status_code=status.HTTP_200_OK, summary="식물 품종 도감 조회 및 검색")
def list_or_search_catalog(
    q: Optional[str] = Query(None, description="품종 국문명 또는 학명(영문명) 검색어"),
    limit: int = Query(10, ge=1, le=50, description="자동완성 결과 최대 개수")
):
    """
    식물 도감 목록을 데이터베이스에서 조회하고, 검색어(q)가 제공되면 한글명 또는 학명(영문명)을 기준으로 대소문자 구분 없이 검색합니다.
    """
    try:
        query = session.supabase.table("plant_catalog").select("*")
        
        if q:
            term = clean_search_term(q)
            if term:
                query = query.or_(f"name.ilike.%{term}%,species.ilike.%{term}%,description.ilike.%{term}%")
            
        response = query.limit(limit).execute()
        
        catalog_items = []
        for item in response.data:
            catalog_items.append(PlantCatalogItem(
                id=item["id"],
                name=item["name"],
                species=item["species"],
                familyName=item.get("family_name"),
                description=item.get("description")
            ))
        return catalog_items
        
    except Exception:
        logger.exception("API 처리 중 오류 발생")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="품종 도감 조회 중 오류가 발생했습니다."
        )
