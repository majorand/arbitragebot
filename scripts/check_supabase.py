import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / '.env')
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
print('url set:', bool(url), 'key set:', bool(key))
if not url or not key:
    raise SystemExit('Missing SUPABASE_URL or SUPABASE_KEY')

client = create_client(url, key)
for table in ['odds', 'trades', 'positions']:
    try:
        resp = client.table(table).select('*', count='exact').limit(5).execute()
        print(f"{table}: count={resp.count}, sample={resp.data}")
    except Exception as e:
        print(f"{table}: error {e}")
