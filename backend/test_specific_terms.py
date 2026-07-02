import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.services.rag.vectorstore import specific_query_terms, tokenize_query

query = "테스트식물 알 수 없음 몬스테라는 물을 얼마나 자주 주어야 하나요?"
print("Query:", query)
print("Tokens:", tokenize_query(query))
print("Specific terms:", specific_query_terms(query))
