import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.db import session

response = session.supabase.table("rag_chunks").select("chunk_id", count="exact").execute()
print("Total rows in rag_chunks:", response.count)
