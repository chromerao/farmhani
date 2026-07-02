from typing import List, Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

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
    return items
