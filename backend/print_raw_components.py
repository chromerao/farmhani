import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.services.rag import vectorstore
from openai import OpenAI

query = "테스트식물 알 수 없음 몬스테라는 물을 얼마나 자주 주어야 하나요?"
openai_key = os.getenv("OPENAI_API_KEY") or vectorstore.settings.OPENAI_API_KEY
openai_client = OpenAI(api_key=openai_key)

res = openai_client.embeddings.create(input=[query], model="text-embedding-3-small")
query_vector = res.data[0].embedding

response = vectorstore.session.supabase.rpc(
    "match_rag_chunks",
    {"query_embedding": query_vector, "match_threshold": 0.25, "match_count": 8}
).execute()

print("--- Raw Vector Results from DB ---")
for i, item in enumerate(response.data or [], 1):
    print(f"[{i}] Similarity: {item.get('similarity')} | Title: {item.get('metadata', {}).get('title')} | Snippet: {item.get('content', '')[:100]}")

keyword_results = vectorstore.supabase_keyword_search(query, 8)
print("\n--- Raw Keyword Results ---")
for i, item in enumerate(keyword_results, 1):
    print(f"[{i}] Score: {item.score} | Title: {item.metadata.get('title')} | Snippet: {item.content[:100]}")
