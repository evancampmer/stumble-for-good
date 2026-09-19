"""
Run this on a schedule (e.g. a cron job every 30-60 min) to refill the 'sites' pool
table from the source APIs. Keeping ingestion separate from request handling means
/api/random never waits on an external API and never fails if one is down.

Usage: python ingest.py
"""
import os
import random
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
PRODUCTHUNT_TOKEN = os.environ.get("PRODUCTHUNT_TOKEN")

def domain_of(url):
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return url

def fetch_hn(n=25):
    ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10).json()
    sample = random.sample(ids[:150], min(n, len(ids[:150])))
    rows = []
    for item_id in sample:
        item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=10).json()
        if not item or not item.get("url"):
            continue
        rows.append({
            "source": "hn", "category": "smarter", "title": item.get("title", "Untitled"),
            "url": item["url"], "domain": domain_of(item["url"]),
            "description": f"{item.get('score', 0)} points on Hacker News, {item.get('descendants', 0)} comments.",
            "thumbnail": None,
        })
    return rows

def fetch_unsplash(n=25):
    if not UNSPLASH_ACCESS_KEY:
        return []
    r = requests.get(
        "https://api.unsplash.com/photos/random",
        params={"client_id": UNSPLASH_ACCESS_KEY, "count": n},
        timeout=10,
    ).json()
    rows = []
    for photo in r if isinstance(r, list) else []:
        rows.append({
            "source": "unsplash", "category": "beautiful",
            "title": photo.get("description") or photo.get("alt_description") or "Untitled photo",
            "url": photo["links"]["html"], "domain": "unsplash.com",
            "description": f"Photo by {photo['user']['name']} on Unsplash.",
            "thumbnail": photo["urls"]["regular"],
        })
    return rows

def fetch_producthunt(n=25):
    if not PRODUCTHUNT_TOKEN:
        return []
    query = "{ posts(order: RANKING, first: %d) { edges { node { name tagline url website thumbnail { url } } } } }" % n
    r = requests.post(
        "https://api.producthunt.com/v2/api/graphql",
        json={"query": query},
        headers={"Authorization": f"Bearer {PRODUCTHUNT_TOKEN}"},
        timeout=10,
    ).json()
    edges = r.get("data", {}).get("posts", {}).get("edges", [])
    rows = []
    for edge in edges:
        node = edge["node"]
        url = node.get("website") or node["url"]
        rows.append({
            "source": "producthunt", "category": "inspire", "title": node["name"], "url": url,
            "domain": "producthunt.com", "description": node.get("tagline", ""),
            "thumbnail": (node.get("thumbnail") or {}).get("url"),
        })
    return rows

def fetch_wiby(n=25):
    rows = []
    for _ in range(n):
        try:
            item = requests.get("https://wiby.me/api/randombytime/", timeout=10).json()
        except Exception:
            continue
        url = item.get("URL") or item.get("Url") or item.get("url")
        if not url:
            continue
        title = item.get("Title") or item.get("title") or url
        rows.append({
            "source": "wiby", "category": "laugh", "title": title, "url": url,
            "domain": domain_of(url), "description": "A random page from the old, weird web via wiby.me.",
            "thumbnail": None,
        })
    return rows

def main():
    all_rows = fetch_hn() + fetch_unsplash() + fetch_producthunt() + fetch_wiby()
    if not all_rows:
        print("No rows fetched — check API keys / network.")
        return
    conn = psycopg2.connect(DATABASE_URL)
    with conn, conn.cursor() as cur:
        for row in all_rows:
            cur.execute(
                """INSERT INTO sites (source, category, title, url, domain, description, thumbnail)
                   VALUES (%(source)s, %(category)s, %(title)s, %(url)s, %(domain)s, %(description)s, %(thumbnail)s)
                   ON CONFLICT (url) DO UPDATE SET fetched_at = now()""",
                row,
            )
    conn.close()
    print(f"Ingested/refreshed {len(all_rows)} rows.")

if __name__ == "__main__":
    main()
