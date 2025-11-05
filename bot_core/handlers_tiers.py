# bot_core/handlers_tiers.py
import os
from telegram import Update
from telegram.ext import ContextTypes
from user_tiers import upgrade_message, save_receipt, mark_paid

ADMIN_ID = os.getenv("ADMIN_ID", "")

# ------------------------------
# 💎 دستور /upgrade برای کاربران
# ------------------------------
async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(upgrade_message())

# ------------------------------
# 📸 دریافت عکس رسید پرداخت
# ------------------------------
async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    photo = update.message.photo[-1].file_id if update.message.photo else None

    if not photo:
        await update.message.reply_text("⚠️ لطفاً یک عکس معتبر از رسید پرداخت ارسال کنید.")
        return

    save_receipt(uid, photo)
    await update.message.reply_text("🧾 رسید پرداخت دریافت شد! لطفاً منتظر تأیید مدیر باشید.")
    await context.bot.send_message(
        ADMIN_ID,
        f"📥 رسید پرداخت جدید از کاربر {uid}.\n"
        f"برای تأیید، از دستور زیر استفاده کنید:\n"
        f"/approve_{uid}_starter یا /approve_{uid}_pro"
    )

# ------------------------------
# 👑 تأیید پرداخت توسط مدیر
# ------------------------------
async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if str(user.id) != ADMIN_ID and str(user.username) != ADMIN_ID:
        return

    text = update.message.text
    if text.startswith("/approve_"):
        try:
            _, uid, tier = text.split("_")
            mark_paid(int(uid), tier)
            await context.bot.send_message(uid, f"✅ اشتراک {tier} شما با موفقیت فعال شد. از خدمات نیکا ویزا لذت ببرید!")
            await update.message.reply_text(f"کاربر {uid} به سطح {tier} ارتقا یافت ✅")
        except Exception as e:
            await update.message.reply_text(f"⚠️ خطا در تأیید: {e}")
# -------------------------------------------------
# 📊 /stats — Admin-only command
# -------------------------------------------------
import os
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

ADMIN_ID = os.getenv("ADMIN_ID")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show total users and recent activity (admin only)."""
    uid = str(update.effective_user.id)
    if uid != str(ADMIN_ID):
        await update.message.reply_text("❌ فقط ادمین می‌تواند این دستور را اجرا کند.")
        return

    try:
        # --- Count users ---
        users_conn = sqlite3.connect("users.db")
        cursor = users_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # --- Count logs ---
        logs_conn = sqlite3.connect("utils/user_logs.db")
        lcursor = logs_conn.cursor()
        lcursor.execute("SELECT COUNT(*) FROM logs")
        total_queries = lcursor.fetchone()[0]

        # --- Recent 5 users ---
        cursor.execute("SELECT username, id FROM users ORDER BY id DESC LIMIT 5")
        recent_users = cursor.fetchall()
        users_conn.close()
        logs_conn.close()

        # --- Build response ---
        msg = f"📊 *Nika Visa Bot Stats*\n\n👥 Total users: {total_users}\n💬 Total queries: {total_queries}\n\n🆕 Recent users:\n"
        for u in recent_users:
            uname = u[0] or "—"
            uid_short = str(u[1])
            msg += f"- @{uname} ({uid_short})\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ خطا در دریافت آمار: {e}")
