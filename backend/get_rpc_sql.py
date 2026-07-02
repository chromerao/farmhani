import os
import sys
sys.path.append(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from app.db import session

# Supabase python client doesn't support raw SQL, but we can query pg_proc table using postgrest!
# Wait, postgrest exposes tables and views, not system catalogs usually, unless they are exposed in the api schema.
# Let's see if we can query it or if it errors.
try:
    res = session.supabase.table("pg_proc").select("*").execute()
    print("Exposed pg_proc!")
except Exception as e:
    print("Cannot query pg_proc directly:", e)

# Wait! We can check if we can query pg_catalog.pg_proc?
try:
    res = session.supabase.table("pg_catalog.pg_proc").select("*").execute()
    print("Exposed pg_catalog.pg_proc!")
except Exception as e:
    print("Cannot query pg_catalog.pg_proc:", e)
