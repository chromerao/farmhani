import os
import json
import sys
from pathlib import Path

# 프로젝트 루트
root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "data" / "scripts"))

from common import uuid_for_chunk_key, uuid_for_source_key

def main():
    print("환경변수 로드 중...")
    env_path = root_dir / ".env"
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'").strip()
                    if k == "SUPABASE_URL" and not supabase_url:
                        supabase_url = v
                    elif k == "SUPABASE_SERVICE_ROLE_KEY" and not supabase_key:
                        supabase_key = v
                    elif k == "OPENAI_API_KEY" and not openai_key:
                        openai_key = v

    if not supabase_url or not supabase_key or not openai_key:
        print("오류: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY 중 누락된 환경변수가 있습니다.")
        print(".env 파일을 다시 확인해 주세요.")
        return

    print("가이드라인 JSON 파일 읽는 중...")
    json_path = root_dir / "data" / "processed" / "gardening_docs.json"
    if not json_path.exists():
        print(f"오류: {json_path} 파일이 없습니다.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    try:
        from supabase import create_client
        from openai import OpenAI
    except ImportError as e:
        print(f"오류: 필요한 라이브러리(supabase, openai)가 누락되었습니다: {e}")
        return

    db = create_client(supabase_url, supabase_key)
    openai_client = OpenAI(api_key=openai_key)

    print("임베딩 데이터 추출 및 Supabase 적재 시작...")
    
    for doc in docs:
        source_key = doc["id"]
        source_id = uuid_for_source_key(source_key)
        title = doc["title"]
        url = doc["url"]
        publisher = doc["publisher"]
        content = doc["content"]
        keywords = doc.get("keywords", [])

        print(f"[{source_id}] 출처 정보 적재 중: {title}")
        db.table("rag_sources").upsert({
            "source_id": source_id,
            "title": title,
            "url": url,
            "publisher": publisher,
            "collected_at": "2026-06-30"
        }, on_conflict="source_id").execute()

        print(f"[{source_id}] 임베딩 생성 중...")
        res = openai_client.embeddings.create(
            input=[content],
            model="text-embedding-3-small"
        )
        embedding_vector = res.data[0].embedding

        print(f"[{source_id}] 1536차원 벡터 데이터베이스 적재 중...")
        chunk_id = uuid_for_chunk_key(f"{source_key}_chunk1")
        
        db.table("rag_chunks").upsert({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "text": content,
            "embedding": embedding_vector,
            "symptom_keywords": keywords
        }, on_conflict="chunk_id").execute()

    print("🎉 성공: 모든 가이드 문서 및 1536차원 벡터 데이터베이스 이관(Seeding)이 완료되었습니다!")

if __name__ == "__main__":
    main()
