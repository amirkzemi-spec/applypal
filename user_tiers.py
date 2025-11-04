# user_tiers.py
import os
import sqlite3
import datetime
from dotenv import load_dotenv

# -------------------------------
# 🔐 Environment & Globals
# -------------------------------
load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = "users.db"

# Developer/test identities (usernames and numeric IDs)
# Add additional IDs/usernames as needed for testing
DEV_IDS = {"@AmirK_19", "AmirK_19", "708110184"}  # keep numeric ID as string for comparison

# -------------------------------
# 🧠 Tier settings
# -------------------------------
TIER_LIMITS = {
    "free": 10,
    "starter": 30,
    "pro": 100
}

TIER_INFO = {
    "free": {
        "name": "رایگان",
        "price": "۰ تومان",
        "features": "۱۰ پیام در روز، متنی و صوتی"
    },
    "starter": {
        "name": "استارتر",
        "price": "۵۹۹,۰۰۰ تومان / ماهانه",
        "features": "۳۰ پیام در روز، شامل پاسخ صوتی و جستجوی هوشمند"
    },
    "pro": {
        "name": "حرفه‌ای",
        "price": "۹۹۹,۰۰۰ تومان / ماهانه",
        "features": "۱۰۰ پیام در روز، شامل همه امکانات و مشاوره تخصصی"
    }
}

# -------------------------------
# 📦 Database helpers
# -------------------------------
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
    cur.execute("SELECT telegram_id, tier, queries_today, last_reset, paid_status, receipt_photo FROM users WHERE telegram_id=?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return row


def add_or_update_user(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = str(datetime.date.today())
    # Use INSERT OR IGNORE then ensure last_reset set
    cur.execute("""
        INSERT OR IGNORE INTO users (telegram_id, last_reset)
        VALUES (?, ?)
    """, (tg_id, today))
    # If user exists but last_reset is NULL, set it
    cur.execute("UPDATE users SET last_reset = COALESCE(last_reset, ?) WHERE telegram_id=?", (today, tg_id))
    conn.commit()
    conn.close()


def reset_if_needed(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = str(datetime.date.today())
    cur.execute("SELECT last_reset FROM users WHERE telegram_id=?", (tg_id,))
    row = cur.fetchone()
    if row and row[0] != today:
        cur.execute("UPDATE users SET queries_today=0, last_reset=? WHERE telegram_id=?", (today, tg_id))
        conn.commit()
    conn.close()


def increment_user_query(tg_id):
    """
    Increase user's query count by 1 unless the tg_id is a developer/test id.
    Accepts either numeric tg_id (int) or string. The DB stores numeric IDs.
    """
    # Developer bypass: do not increment counter for testing IDs
    if str(tg_id) in DEV_IDS:
        print(f"👨‍💻 increment_user_query: developer/test ID {tg_id} — skipping increment.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET queries_today = IFNULL(queries_today, 0) + 1 WHERE telegram_id=?", (tg_id,))
    conn.commit()
    conn.close()

# -------------------------------
# ⏳ Subscription expiry helpers
# -------------------------------
def downgrade_user(tg_id):
    """در صورت اتمام مهلت اشتراک، کاربر به پلن رایگان برگردانده می‌شود."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET tier='free', paid_status=0, queries_today=0 WHERE telegram_id=?",
        (tg_id,)
    )
    conn.commit()
    conn.close()
    print(f"🔁 User {tg_id} downgraded to Free (subscription expired).")


def mark_paid(tg_id, tier):
    """ثبت پرداخت و شروع دوره‌ی ۳۰ روزه جدید"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = str(datetime.date.today())
    cur.execute(
        "UPDATE users SET tier=?, paid_status=1, last_reset=? WHERE telegram_id=?",
        (tier, today, tg_id)
    )
    conn.commit()
    conn.close()


def days_remaining(tg_id):
    """محاسبه‌ی تعداد روز باقی‌مانده از اشتراک"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tier, paid_status, last_reset FROM users WHERE telegram_id=?", (tg_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return 0, "free"

    tier, paid_status, last_reset = row
    if tier in ["starter", "pro"] and paid_status == 1 and last_reset:
        try:
            start_date = datetime.datetime.strptime(last_reset, "%Y-%m-%d").date()
            elapsed = (datetime.date.today() - start_date).days
            remaining = max(0, 30 - elapsed)
            return remaining, tier
        except Exception:
            return 0, tier
    return 0, tier

# -------------------------------
# 🚦 Main logic (single definitive function)
# -------------------------------
def check_user_limit(tg_id):
    """
    بررسی محدودیت روزانه و تاریخ انقضای اشتراک کاربر
    Returns: (ok: bool, message: str)
    """

    # Developer bypass (username or numeric id)
    if str(tg_id) in DEV_IDS:
        print(f"👨‍💻 Developer bypass active for {tg_id}")
        return True, "Developer unlimited mode active ✅"

    # Ensure user row exists and reset if a new day
    add_or_update_user(tg_id)
    reset_if_needed(tg_id)
    user = get_user(tg_id)

    if not user:
        return True, "کاربر جدید ثبت شد."

    tier = user[1] or "free"
    queries_today = user[2] or 0
    limit = TIER_LIMITS.get(tier, 10)

    # 🗓️ بررسی انقضای اشتراک
    remaining_days, current_tier = days_remaining(tg_id)
    if current_tier in ["starter", "pro"]:
        if remaining_days == 0:
            downgrade_user(tg_id)
            tier = "free"
        elif remaining_days <= 3:
            reminder = (
                f"📅 اشتراک {TIER_INFO[current_tier]['name']} شما در {remaining_days} روز آینده منقضی می‌شود.\n"
                "برای تمدید، لطفاً با پشتیبان تماس بگیرید:\n"
                "👉 [@nikavisa_admin](https://t.me/nikavisa_admin)"
            )
            return True, reminder

    # 💬 بررسی محدودیت روزانه
    if queries_today >= limit:
        msg = (
            f"⛔️ شما به سقف مجاز پیام‌های روزانه در پلن {TIER_INFO[tier]['name']} خود رسیده‌اید.\n\n"
            "🕓 می‌توانید پس از ۲۴ ساعت دوباره تلاش کنید، یا یکی از پلن‌های زیر را فعال نمایید:\n\n"
            "🟡 پلن استارتر: ۳۰ پیام در روز — ۵۹۹,۰۰۰ تومان / ماهانه\n"
            "🔵 پلن حرفه‌ای (Pro): ۱۰۰ پیام در روز — ۹۹۹,۰۰۰ تومان / ماهانه\n\n"
            "برای ارتقا و فعال‌سازی پلن، لطفاً از طریق تلگرام با پشتیبان تماس بگیرید:\n"
            "👉 [@nikavisa_admin](https://t.me/nikavisa_admin)"
        )
        return False, msg

    return True, ""

# -------------------------------
# 🧾 Tier utilities
# -------------------------------
def get_user_tier(tg_id):
    user = get_user(tg_id)
    return user[1] if user else "free"


def save_receipt(tg_id, file_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET receipt_photo=? WHERE telegram_id=?", (file_id, tg_id))
    conn.commit()
    conn.close()


def upgrade_message():
    return (
        "💳 ارتقای پلن:\n\n"
        "🟡 پلن استارتر — ۵۹۹,۰۰۰ تومان / ماهانه (۳۰ پیام در روز)\n"
        "🔵 پلن حرفه‌ای — ۹۹۹,۰۰۰ تومان / ماهانه (۱۰۰ پیام در روز)\n\n"
        "برای ارتقا و تمدید اشتراک، لطفاً از طریق تلگرام با پشتیبان تماس بگیرید:\n"
        "👉 [@nikavisa_admin](https://t.me/nikavisa_admin)"
    )
def get_user_count():
    import sqlite3
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_active_users_today():
    import sqlite3, datetime
    today = str(datetime.date.today())
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE last_reset=?", (today,))
    count = cur.fetchone()[0]
    conn.close()
    return count
