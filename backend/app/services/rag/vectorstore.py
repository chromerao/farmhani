import os
import json
from pathlib import Path
from typing import List, Dict, Any

from app.db import session

# 프로젝트 루트 경로 (Fallback 파일 조회용)
backend_dir = Path(__file__).resolve().parents[4]
docs_json_path = backend_dir / "data" / "processed" / "gardening_docs.json"

class SearchResult:
    def __init__(self, content: str, metadata: Dict[str, Any], score: float):
        self.content = content
        self.metadata = metadata
        self.score = score

def fallback_keyword_search(query: str, top_k: int = 3) -> List[SearchResult]:
    """
    OpenAI API Key 또는 pgvector RPC가 없는 환경에서 동작하는 텍스트 기반 키워드 매칭 검색기입니다.
    """
    if not docs_json_path.exists():
        print(f"[Fallback Search] 가이드 문서 파일이 존재하지 않습니다: {docs_json_path}")
        return []
        
    with open(docs_json_path, "r", encoding="utf-8") as f:
        docs = json.load(f)
        
    clean_query = query.replace(",", " ").replace("?", " ").replace(".", " ")
    query_tokens = [token.strip() for token in clean_query.split() if len(token) > 0]
    
    results = []
    for doc in docs:
        score = 0.0
        for token in query_tokens:
            for keyword in doc.get("keywords", []):
                if token in keyword or keyword in token:
                    score += 2.0
            if token in doc["content"]:
                score += 1.0
                
        if score > 0.0:
            metadata = {
                "source_id": doc["id"],
                "title": doc["title"],
                "url": doc["url"],
                "publisher": doc["publisher"]
            }
            results.append(SearchResult(
                content=doc["content"],
                metadata=metadata,
                score=score
            ))
            
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]

def search_documents(query: str, top_k: int = 3) -> List[SearchResult]:
    """
    최적의 수단을 사용하여 지침 문서를 검색합니다.
    1순위: OpenAI Embedding + Supabase pgvector RPC 호출
    2순위: 텍스트 기반 로컬 키워드 매칭 Fallback 엔진
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if openai_key:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=openai_key)
            
            # 1. OpenAI 임베딩 생성 (1536차원)
            res = openai_client.embeddings.create(
                input=[query],
                model="text-embedding-3-small"
            )
            query_vector = res.data[0].embedding
            
            # 2. Supabase RPC match_rag_chunks 호출
            response = session.supabase.rpc(
                "match_rag_chunks",
                {
                    "query_embedding": query_vector,
                    "match_threshold": 0.3,
                    "match_count": top_k
                }
            ).execute()
            
            results = []
            for item in response.data:
                metadata = {
                    "source_id": item["source_id"],
                    "title": item["title"],
                    "url": item.get("url"),
                    "publisher": item.get("publisher")
                }
                results.append(SearchResult(
                    content=item["content"],
                    metadata=metadata,
                    score=float(item["similarity"])
                ))
            return results
        except Exception as e:
            print(f"[RAG SEARCH WARNING] Supabase pgvector RPC 검색 중 오류 발생, Fallback 우회: {e}")
            return fallback_keyword_search(query, top_k)
    else:
        return fallback_keyword_search(query, top_k)
