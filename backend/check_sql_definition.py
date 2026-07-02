import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
import urllib.parse

db_url = os.getenv("DATABASE_URL").strip()
print("Connecting to:", db_url.split("@")[-1])

# Try connecting using psycopg2
try:
    import psycopg2
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
    SELECT routine_definition 
    FROM information_schema.routines 
    WHERE routine_name = 'match_rag_chunks';
    """)
    res = cur.fetchone()
    if res:
        print("\n--- match_rag_chunks SQL Definition ---")
        print(res[0])
    else:
        print("Function match_rag_chunks not found in information_schema.routines")
    cur.close()
    conn.close()
except Exception as e:
    print("Failed with psycopg2:", e)

