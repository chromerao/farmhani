import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.services.rag import vectorstore

def clean_korean_particle(word: str) -> str:
    particles = ["는", "은", "를", "을", "가", "이", "의", "에", "와", "과", "로", "으로", "에서"]
    for p in particles:
        if word.endswith(p) and len(word) > len(p):
            return word[:-len(p)]
    return word

def specific_query_terms_improved(query: str) -> list:
    raw_tokens = vectorstore.tokenize_query(query)
    cleaned = []
    for t in raw_tokens:
        t_clean = clean_korean_particle(t)
        if t_clean not in vectorstore.CARE_TERMS and len(t_clean) >= 2:
            cleaned.append(t_clean)
    return cleaned

vectorstore.specific_query_terms = specific_query_terms_improved

query = "테스트식물 알 수 없음 몬스테라는 물을 얼마나 자주 주어야 하나요?"
# We will manually run parts of search_documents
openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
from openai import OpenAI
openai_client = OpenAI(api_key=openai_key)

res = openai_client.embeddings.create(input=[query], model="text-embedding-3-small")
query_vector = res.data[0].embedding

response = vectorstore.session.supabase.rpc(
    "match_rag_chunks",
    {"query_embedding": query_vector, "match_threshold": 0.25, "match_count": 8}
).execute()

vector_results = []
for item in response.data or []:
    vector_results.append(vectorstore.SearchResult(
        content=item.get("content") or item.get("text") or "",
        metadata=vectorstore.normalize_metadata(item),
        score=float(item.get("similarity") or item.get("score") or 0.0)
    ))

keyword_results = vectorstore.supabase_keyword_search(query, 8)
merged = vectorstore.merge_results(keyword_results, vector_results, top_k=8)

print("--- Merged Results BEFORE Filtering ---")
for i, d in enumerate(merged, 1):
    print(f"[{i}] Score: {d.score:.4f} | Title: {d.metadata.get('title')} | Snippet: {d.content[:50]}")

terms = specific_query_terms_improved(query)
print("\nSpecific terms:", terms)

print("\n--- Filtering Process ---")
for i, result in enumerate(merged, 1):
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
    matches = [term for term in terms if term.lower() in haystack]
    print(f"[{i}] Title: {metadata.get('title')} | Matched terms: {matches}")
