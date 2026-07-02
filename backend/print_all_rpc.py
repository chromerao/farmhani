import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.db import session
from app.core.config import settings
from openai import OpenAI

query = "테스트식물 알 수 없음 몬스테라는 물을 얼마나 자주 주어야 하나요?"
openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
openai_client = OpenAI(api_key=openai_key)
res = openai_client.embeddings.create(input=[query], model="text-embedding-3-small")
query_vector = res.data[0].embedding

response = session.supabase.rpc(
    "match_rag_chunks",
    {
        "query_embedding": query_vector,
        "match_threshold": -1.0,
        "match_count": 10
    }
).execute()

for i, item in enumerate(response.data or [], 1):
    title = item.get("metadata", {}).get("title") or item.get("title") or ""
    similarity = item.get("similarity")
    print(f"[{i}] Similarity: {similarity} | Title: {title}")
