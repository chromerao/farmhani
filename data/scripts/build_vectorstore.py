import os
import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "data" / "scripts"))

from common import uuid_for_source_key

def main():
    print("가이드 문서 데이터셋 로드 중...")
    json_path = root_dir / "data" / "processed" / "gardening_docs.json"
    if not json_path.exists():
        print(f"오류: {json_path} 파일이 존재하지 않습니다.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    # env 파일 로드 시도
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        env_path = root_dir / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as ef:
                for line in ef:
                    if line.startswith("OPENAI_API_KEY="):
                        openai_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        os.environ["OPENAI_API_KEY"] = openai_key
                        break

    if not openai_key:
        print("경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("로컬 벡터스토어 빌드를 위해서는 OpenAI API Key가 필요합니다.")
        print("다만, 백엔드는 Key가 없을 시 텍스트 기반 Fallback 매칭 엔진으로 자동 전환되므로 안심하셔도 됩니다.")
        return

    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
    except ImportError as e:
        print(f"오류: 빌드에 필요한 langchain 관련 패키지가 누락되었습니다: {e}")
        print("가상환경에서 pip install langchain-openai langchain-community faiss-cpu 명령을 실행해 주세요.")
        return

    print("문서 벡터화 진행 중...")
    documents = []
    for doc in docs:
        metadata = {
            "source_id": uuid_for_source_key(doc["id"]),
            "source_key": doc["id"],
            "title": doc["title"],
            "url": doc["url"],
            "publisher": doc["publisher"]
        }
        documents.append(Document(page_content=doc["content"], metadata=metadata))

    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = FAISS.from_documents(documents, embeddings)
        
        output_dir = root_dir / "data" / "vectorstore"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        vectorstore.save_local(str(output_dir))
        print(f"성공: 로컬 벡터스토어가 {output_dir} 경로에 저장되었습니다!")
    except Exception as e:
        print(f"오류: 벡터스토어 빌딩 중 예외 발생: {str(e)}")

if __name__ == "__main__":
    main()
