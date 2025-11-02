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
