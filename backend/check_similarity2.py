import os
import sys
import json
import math
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.db import session
from openai import OpenAI

def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def norm(v):
    return math.sqrt(sum(x * x for x in v))

def cosine_similarity(v1, v2):
    n1 = norm(v1)
    n2 = norm(v2)
    if n1 == 0 or n2 == 0:
        return 0
    return dot_product(v1, v2) / (n1 * n2)

query = "테스트식물 알 수 없음 몬스테라는 물을 얼마나 자주 주어야 하나요?"
client = OpenAI()
res = client.embeddings.create(input=[query], model="text-embedding-3-small")
query_vector = res.data[0].embedding
print("Query Vector Dim:", len(query_vector))

response = session.supabase.table("rag_chunks").select("chunk_id,text,embedding").ilike("text", "%몬스테라%").execute()
for i, item in enumerate(response.data or [], 1):
    text = item.get("text") or ""
    emb_str = item.get("embedding")
    if not emb_str:
        print(f"[{i}] No embedding")
        continue
    try:
        emb = json.loads(emb_str)
    except Exception as e:
        clean = emb_str.strip().strip("[]")
        emb = [float(x) for x in clean.split(",") if x.strip()]
        
    print(f"\n[{i}] Doc Dim: {len(emb)} | Snippet: {text[:80]}")
    sim = cosine_similarity(query_vector, emb)
    print(f"Cosine Similarity: {sim:.4f}")
