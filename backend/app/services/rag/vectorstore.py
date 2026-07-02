import os
import json
from pathlib import Path
from typing import List, Dict, Any

from app.db import session
from app.core.config import settings

# 프로젝트 루트 경로 (Fallback 파일 조회용)
backend_dir = Path(__file__).resolve().parents[4]
docs_json_path = backend_dir / "data" / "processed" / "gardening_docs.json"
SUPABASE_KEYWORD_SCAN_LIMIT = 3000

class SearchResult:
    def __init__(self, content: str, metadata: Dict[str, Any], score: float):
        self.content = content
        self.metadata = metadata
        self.score = score


STOPWORDS = {
    "식물", "작물", "사진", "분석", "상태", "관리", "질문", "현재", "공식", "문서",
    "어떻게", "해주세요", "알려줘", "알려주세요", "가능성", "상담", "진단",
    "plant", "care", "photo", "image", "document", "official",
}

CARE_TERMS = {
    "물주기", "물관리", "키우기", "키우는", "방법", "관리법", "가이드", "재배", "재배법",
    "햇빛", "광량", "온도", "습도", "흙", "분갈이", "비료", "병해충", "잎", "줄기",
    "수분공급", "관수", "생육", "건조", "과습", "일반", "황화", "갈변", "시듦",
}

PLANT_QUERY_TERMS = {
    "몬스테라", "스투키", "산세베리아", "선인장", "금전수", "테이블야자", "홍콩야자", "호접란",
    "스파티필럼", "보스턴고사리", "부레옥잠", "올리브나무", "오렌지쟈스민", "관음죽",
    "벵갈고무나무", "디펜바키아", "토마토", "고추", "상추", "배추", "파프리카", "양배추",
    "딸기", "감자", "고구마", "장미", "벚꽃", "개나리", "해바라기", "국화", "라벤더",
    "로즈마리", "바질", "민트", "깻잎", "오이", "호박", "가지", "마늘", "양파", "부추",
}

PLANT_ALIASES = {
    "monstera": "몬스테라",
    "deliciosa": "몬스테라",
    "sansevieria": "스투키",
    "dracaena": "스투키",
    "zamioculcas": "금전수",
    "spathiphyllum": "스파티필럼",
    "orchid": "호접란",
    "phalaenopsis": "호접란",
    "tomato": "토마토",
    "lycopersicum": "토마토",
    "capsicum": "고추",
    "pepper": "고추",
    "lettuce": "상추",
    "lactuca": "상추",
    "strawberry": "딸기",
    "fragaria": "딸기",
    "potato": "감자",
    "solanum": "감자",
    "sweet": "고구마",
    "rose": "장미",
    "rosa": "장미",
    "helianthus": "해바라기",
    "forsythia": "개나리",
}


def expand_query_aliases(query: str) -> str:
    lower_query = query.lower()
    aliases = [alias for key, alias in PLANT_ALIASES.items() if key in lower_query]
    if not aliases:
        return query
    return f"{query} {' '.join(dict.fromkeys(aliases))}"


def tokenize_query(query: str) -> List[str]:
    query = expand_query_aliases(query)
    clean_query = query.replace(",", " ").replace("?", " ").replace(".", " ").replace("/", " ")
    tokens = []
    for token in clean_query.split():
        token = token.strip().lower()
        if len(token) <= 1 or token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def specific_query_terms(query: str) -> List[str]:
    particles = ["는", "은", "를", "을", "가", "이", "의", "에", "와", "과", "로", "으로", "에서"]
    specific = []
    for token in tokenize_query(query):
        cleaned = token
        for particle in particles:
            if token.endswith(particle) and len(token) > len(particle):
                cleaned = token[: -len(particle)]
                break
        if cleaned not in CARE_TERMS and len(cleaned) >= 2:
            specific.append(cleaned)
    return specific


def filter_by_specific_terms(query: str, results: List[SearchResult]) -> List[SearchResult]:
    terms = specific_query_terms(query)
    if not terms:
        return results
    plant_terms = [term for term in terms if term in PLANT_QUERY_TERMS]

    filtered = []
    for result in results:
        metadata = result.metadata or {}
        haystack = " ".join(
            str(part or "")
            for part in [
                result.content,
                metadata.get("title"),
                metadata.get("section"),
                metadata.get("excerpt"),
            ]
        ).lower()
        if plant_terms:
            title_haystack = " ".join(
                str(part or "")
                for part in [
                    metadata.get("title"),
                    metadata.get("section"),
                    metadata.get("excerpt"),
                ]
            ).lower()
            title_plant_terms = [term for term in PLANT_QUERY_TERMS if term.lower() in title_haystack]
            if title_plant_terms and not any(term in plant_terms for term in title_plant_terms):
                continue
            if any(term.lower() in haystack for term in plant_terms):
                filtered.append(result)
            continue
        if any(term.lower() in haystack for term in terms):
            filtered.append(result)
    return filtered

def normalize_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    nested_source = item.get("rag_sources") if isinstance(item.get("rag_sources"), dict) else {}
    return {
        "chunk_id": item.get("chunk_id") or item.get("id") or metadata.get("chunkId") or metadata.get("chunk_id"),
        "source_id": item.get("source_id") or metadata.get("sourceId") or metadata.get("source_id") or "",
        "title": item.get("title") or metadata.get("title") or nested_source.get("title") or "출처 미상",
        "url": item.get("url") or metadata.get("url") or nested_source.get("url"),
        "publisher": item.get("publisher") or metadata.get("publisher") or nested_source.get("publisher"),
        "section": item.get("section") or metadata.get("section") or metadata.get("category"),
        "excerpt": item.get("excerpt") or metadata.get("excerpt") or metadata.get("contentPreview"),
    }

def score_text(query_tokens: List[str], text: str, keywords: List[str]) -> float:
    score = 0.0
    lower_text = text.lower()
    lower_keywords = [str(keyword).lower() for keyword in keywords]
    stopwords = {"식물", "작물", "사진", "분석", "상태", "관리", "질문", "알려줘", "현재", "기준", "공식", "문서"}
    for token in query_tokens:
        token_lower = token.lower()
        if not token_lower or token_lower in stopwords:
            continue
        if token_lower in lower_text:
            score += 2.0 if len(token_lower) >= 3 else 1.0
        for keyword in lower_keywords:
            if token_lower in keyword or keyword in token_lower:
                score += 2.0
    return score


def merge_results(*groups: List[SearchResult], top_k: int, rrf_k: int = 60) -> List[SearchResult]:
    # RRF (Reciprocal Rank Fusion) 알고리즘 적용
    rrf_scores: dict[str, float] = {}
    merged_results: dict[str, SearchResult] = {}
    
    for group in groups:
        # group은 이미 자신의 점수로 정렬되어 있다고 가정
        for rank, result in enumerate(group):
            metadata = result.metadata or {}
            key = str(metadata.get("chunk_id") or metadata.get("id") or result.content[:120])
            
            # RRF 점수 누적
            if key not in rrf_scores:
                rrf_scores[key] = 0.0
                merged_results[key] = result
            
            rrf_scores[key] += 1.0 / (rank + 1 + rrf_k)
            
    # 누적된 RRF 점수로 갱신
    for key, result in merged_results.items():
        result.score = rrf_scores[key]
        
    return sorted(merged_results.values(), key=lambda item: item.score, reverse=True)[:top_k]

def supabase_keyword_search(query: str, top_k: int = 3) -> List[SearchResult]:
    """
    pgvector RPC가 없거나 스키마 버전 차이로 실패하는 환경에서 Supabase RAG 테이블을 직접 읽는 fallback입니다.
    데이터팀 최신 스키마인 rag_chunks.text / symptom_keywords / metadata를 우선 사용합니다.
    """
    query_tokens = tokenize_query(query)
    if not query_tokens:
        return []

    rows: list[Dict[str, Any]] = []
    selects = [
        "chunk_id,source_id,text,symptom_keywords,metadata,rag_sources(title,url,publisher)",
        "chunk_id,source_id,text,symptom_keywords,rag_sources(title,url,publisher)",
        "id,source_id,content,metadata,rag_sources(title,url,publisher)",
        "id,source_id,content,rag_sources(title,url,publisher)",
    ]
    last_error: Exception | None = None
    for select_clause in selects:
        try:
            start = 0
            page_size = 500
            while start < SUPABASE_KEYWORD_SCAN_LIMIT:
                response = (
                    session.supabase.table("rag_chunks")
                    .select(select_clause)
                    .range(start, start + page_size - 1)
                    .execute()
                )
                page = response.data or []
                rows.extend(page)
                if len(page) < page_size:
                    break
                start += page_size
            break
        except Exception as exc:
            last_error = exc
            rows = []
    if not rows and last_error is not None:
        print(f"[RAG SEARCH WARNING] Supabase keyword fallback 조회 실패: {last_error}")
        return []

    results = []
    for item in rows:
        content = item.get("text") or item.get("content") or ""
        if not content:
            continue
        keywords = item.get("symptom_keywords") or []
        if not isinstance(keywords, list):
            keywords = [str(keywords)]
        score = score_text(query_tokens, content, keywords)
        if score >= 2.0:
            results.append(SearchResult(content=content, metadata=normalize_metadata(item), score=score))

    results.sort(key=lambda result: result.score, reverse=True)
    return results[:top_k]

def fallback_keyword_search(query: str, top_k: int = 3) -> List[SearchResult]:
    """
    OpenAI API Key 또는 pgvector RPC가 없는 환경에서 동작하는 텍스트 기반 키워드 매칭 검색기입니다.
    """
    if not docs_json_path.exists():
        print(f"[Fallback Search] 가이드 문서 파일이 존재하지 않습니다: {docs_json_path}")
        return []
        
    with open(docs_json_path, "r", encoding="utf-8") as f:
        docs = json.load(f)
        
    query_tokens = tokenize_query(query)
    
    results = []
    for doc in docs:
        score = 0.0
        for token in query_tokens:
            for keyword in doc.get("keywords", []):
                if token in keyword or keyword in token:
                    score += 2.0
            if token in doc["content"]:
                score += 1.0
                
        if score >= 2.0:
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

def search_documents(query: str, top_k: int = 8) -> List[SearchResult]:
    """
    최적의 수단을 사용하여 지침 문서를 검색합니다.
    1순위: OpenAI Embedding + Supabase pgvector RPC 호출
    2순위: 텍스트 기반 로컬 키워드 매칭 Fallback 엔진
    """
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
    
    if openai_key:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=openai_key, timeout=10.0, max_retries=0)
            
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
                    "match_threshold": 0.32,
                    "match_count": top_k
                }
            ).execute()
            
            vector_results = []
            for item in response.data or []:
                content = item.get("content") or item.get("text") or ""
                if not content:
                    continue
                metadata = normalize_metadata(item)
                vector_results.append(SearchResult(
                    content=content,
                    metadata=metadata,
                    score=float(item.get("similarity") or item.get("score") or 0.0)
                ))
            keyword_results = supabase_keyword_search(query, top_k)
            if vector_results or keyword_results:
                merged_results = merge_results(keyword_results, vector_results, top_k=top_k)
                return filter_by_specific_terms(query, merged_results)[:top_k]
        except Exception as e:
            print(f"[RAG SEARCH WARNING] Supabase pgvector RPC 검색 중 오류 발생, Supabase keyword fallback 전환: {e}")

    supabase_results = supabase_keyword_search(query, top_k)
    if supabase_results:
        return filter_by_specific_terms(query, supabase_results)[:top_k]
    return filter_by_specific_terms(query, fallback_keyword_search(query, top_k))[:top_k]
