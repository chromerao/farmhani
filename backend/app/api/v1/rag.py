from typing import List, Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.db.session import supabase
from app.services.rag.vectorstore import search_documents

router = APIRouter(prefix="/rag", tags=["RAG Search"])


class RagSearchResult(BaseModel):
    sourceId: str = Field(..., description="문서 출처 식별자")
    title: str = Field(..., description="출처 문서 제목")
    url: Optional[str] = Field(None, description="원문 URL")
    publisher: Optional[str] = Field(None, description="발행 기관")
    excerpt: str = Field(..., description="검색어와 관련된 문서 발췌문")
    score: Optional[float] = Field(None, description="검색 점수")


def _excerpt(text: str, max_len: int = 180) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rstrip() + "..."


@router.get("/search", response_model=List[RagSearchResult], status_code=status.HTTP_200_OK, summary="공식 RAG 문서 검색")
async def search_rag_documents(
    q: str = Query(..., min_length=1, description="검색할 식물 관리/증상 키워드"),
    limit: int = Query(5, ge=1, le=10, description="검색 결과 최대 개수"),
):
    results = search_documents(q, top_k=limit)
    items: List[RagSearchResult] = []
    for result in results:
        metadata = result.metadata or {}
        items.append(
            RagSearchResult(
                sourceId=metadata.get("source_id") or metadata.get("sourceId") or "unknown",
                title=metadata.get("title") or "출처 미상",
                url=metadata.get("url"),
                publisher=metadata.get("publisher"),
                excerpt=_excerpt(result.content),
                score=result.score,
            )
        )
    if not items:
        try:
            safe_query = q.replace(",", " ").strip()
            catalog_response = (
                supabase.table("plant_catalog")
                .select("id,name,species,family_name,description")
                .or_(f"name.ilike.%{safe_query}%,species.ilike.%{safe_query}%,description.ilike.%{safe_query}%")
                .limit(limit)
                .execute()
            )
            for row in catalog_response.data or []:
                name = row.get("name") or "식물 도감 항목"
                species = row.get("species") or ""
                family_name = row.get("family_name") or ""
                description = row.get("description") or ""
                excerpt_parts = [part for part in [species, family_name, description] if part]
                items.append(
                    RagSearchResult(
                        sourceId=f"plant_catalog:{row.get('id') or name}",
                        title=f"식물 도감 - {name}",
                        url=None,
                        publisher="Farm하니 식물 도감",
                        excerpt=" / ".join(excerpt_parts) or name,
                        score=0.0,
                    )
                )
        except Exception:
            pass
    return items
