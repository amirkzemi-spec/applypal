import sqlite3, datetime

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            tier TEXT DEFAULT 'free',
            queries_today INTEGER DEFAULT 0,
            last_reset TEXT,
            paid_status INTEGER DEFAULT 0,
            receipt_photo TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_or_update_user(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = str(datetime.date.today())
    cur.execute("""
        INSERT INTO users (telegram_id, last_reset) VALUES (?, ?)
        ON CONFLICT(telegram_id) DO NOTHING
    """, (tg_id, today))
    conn.commit()
    conn.close()

def reset_if_needed(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = str(datetime.date.today())
    cur.execute("SELECT last_reset, queries_today FROM users WHERE telegram_id=?", (tg_id,))
    row = cur.fetchone()
    if row:
        last_reset, q_today = row
        if last_reset != today:
            cur.execute("UPDATE users SET queries_today=0, last_reset=? WHERE telegram_id=?", (today, tg_id))
            conn.commit()
    conn.close()

def increment_query(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET queries_today = queries_today + 1 WHERE telegram_id=?", (tg_id,))
    conn.commit()
    conn.close()

def mark_paid(tg_id, tier):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET tier=?, paid_status=1 WHERE telegram_id=?", (tier, tg_id))
    conn.commit()
    conn.close()

def save_receipt(tg_id, file_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET receipt_photo=? WHERE telegram_id=?", (file_id, tg_id))
    conn.commit()
    conn.close()
