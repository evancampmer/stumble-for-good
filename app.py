import os
from flask import Flask, jsonify, request, session, render_template
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def home():
    return app.send_static_file("index.html")

from urllib.parse import urlparse

CATEGORY_SLUG_TO_LABEL = {
    "smarter": "Make Me Smarter",
    "inspire": "Inspire Me",
    "laugh": "Make Me Laugh",
    "beautiful": "Show Me Something Beautiful",
    "enlighten": "Enlighten Me",
}
CATEGORY_LABEL_TO_SLUG = {v: k for k, v in CATEGORY_SLUG_TO_LABEL.items()}

@app.route("/api/random")
def api_random():
    slug = request.args.get("category")
    label = None
    if slug:
        label = CATEGORY_SLUG_TO_LABEL.get(slug)
        if label is None:
            return jsonify({"error": "unknown category"}), 400

    conn = get_db()
    with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if label:
            cur.execute(
                """SELECT title, url, description, thumbnail_url, category
                   FROM media_content
                   WHERE active = true AND category = %s
                   ORDER BY random() LIMIT 1""",
                (label,),
            )
        else:
            cur.execute(
                """SELECT title, url, description, thumbnail_url, category
                   FROM media_content
                   WHERE active = true
                   ORDER BY random() LIMIT 1"""
            )
        row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "pool is empty for this category"}), 502

    domain = urlparse(row["url"]).netloc.replace("www.", "") if row["url"] else ""
    return jsonify({
        "title": row["title"],
        "url": row["url"],
        "description": row["description"],
        "thumbnail": row["thumbnail_url"],
        "domain": domain,
        "category": CATEGORY_LABEL_TO_SLUG.get(row["category"]),
    })

def ensure_session():
    if "session_id" not in session:
        session["session_id"] = os.urandom(16).hex()
    return session["session_id"]

@app.route("/api/save", methods=["POST"])
def api_save():
    sid = ensure_session()
    data = request.get_json(force=True)
    conn = get_db()
    with conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO saved_sites (session_id, url, title, description, domain, category, thumbnail)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (session_id, url) DO NOTHING""",
            (sid, data.get("url"), data.get("title"), data.get("description"), data.get("domain"), data.get("category"), data.get("thumbnail")),
        )
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/unsave", methods=["POST"])
def api_unsave():
    sid = ensure_session()
    data = request.get_json(force=True)
    conn = get_db()
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM saved_sites WHERE session_id = %s AND url = %s", (sid, data.get("url")))
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/saved")
def api_saved():
    sid = ensure_session()
    conn = get_db()
    with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT url, title, description, domain, category, thumbnail FROM saved_sites WHERE session_id = %s ORDER BY created_at DESC",
            (sid,),
        )
        rows = cur.fetchall()
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
