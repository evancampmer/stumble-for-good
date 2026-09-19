import os
import psycopg2
import requests
import time
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT thumbnail_url FROM media_content WHERE thumbnail_url IS NOT NULL")
urls = [r[0] for r in cur.fetchall()]
conn.close()

for i, url in enumerate(urls):
    try:
        requests.get(url, timeout=10)
    except Exception:
        pass
    if i % 20 == 0:
        print(f"{i}/{len(urls)}")
    time.sleep(0.3)

print("done")