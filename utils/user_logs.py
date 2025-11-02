# utils/user_logs.py
import sqlite3, os, datetime
DB_PATH = os.path.join(os.path.dirname(__file__), "user_logs.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        username TEXT,
        query TEXT,
        detected_country TEXT,
        detected_category TEXT,
        created_at TEXT
    )
    """)
    conn.commit(); conn.close()

def save_log(user_id, username, query, country=None, category=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO logs (user_id, username, query, detected_country, detected_category, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, query, country, category, datetime.datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
