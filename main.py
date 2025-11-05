import importlib.util, sys
spec = importlib.util.find_spec("telegram")
print("📦 telegram module path:", spec.origin if spec else "NOT FOUND")
print("🐍 Python:", sys.version)

import os
import time
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -------------------------------
# 🔐 Environment setup
# -------------------------------
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()
    print("📦 Local .env loaded.")
else:
    print("☁️ Running on Railway — env vars injected automatically.")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN missing — check Railway Variables tab")
if not OPENAI_KEY:
    print("⚠️ OPENAI_API_KEY missing — GPT or voice features may fail")

# -------------------------------
# 🪵 Logging setup
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------------------
# 🗄️ Local DBs
# -------------------------------
from user_tiers import init_db as init_tiers_db
from utils.user_logs import init_db as init_logs_db

init_tiers_db()
init_logs_db()
print("✅ Local databases initialized.")

# -------------------------------
# 🧩 Core Handlers
# -------------------------------
from bot_core.handlers_basic import start, handle_text, handle_voice
from bot_core.handlers_tiers import upgrade, handle_receipt, admin_approve, show_stats


# -------------------------------
# 🎓 Inline button callbacks
# -------------------------------
async def study_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle study level inline buttons."""
    query = update.callback_query
    await query.answer()

    level_map = {
        "study_highschool": "دیپلم دبیرستان",
        "study_bachelor": "کارشناسی",
        "study_master": "کارشناسی ارشد",
        "study_phd": "دکترا",
    }
    selected = level_map.get(query.data, "نامشخص")
    context.user_data["education_level"] = selected

    await query.message.reply_text(f"🎓 عالی! رشته یا زمینه تحصیلی‌ات چیست؟ ({selected})")


async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection inline buttons."""
    query = update.callback_query
    await query.answer()
    selected = query.data.split("_")[1]
    context.user_data["preferred_country"] = selected

    await query.message.reply_text(
        f"🌍 کشور انتخابی شما: {selected}. لطفاً سطح زبان یا نمره آیلتس خود را بنویسید."
    )


# -------------------------------
# 🤖 Bot Runner
# -------------------------------
def main():
    logger.info("🚀 Starting bot using ApplicationBuilder...")

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .build()
    )

    # --- Command Handlers ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("approve", admin_approve))

    # --- Admin control ---
    app.add_handler(CommandHandler("stats", show_stats))

    # --- Message Handlers ---
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # --- Inline Callbacks ---
    app.add_handler(CallbackQueryHandler(study_level_callback, pattern="^study_"))
    app.add_handler(CallbackQueryHandler(country_callback, pattern="^country_"))

    logger.info("🤖 Bot is now polling for updates (drop_pending_updates=True)...")
    # ✅ Drop old updates to prevent duplicate /start replies
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


# -------------------------------
# 🏁 Entry Point
# -------------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"💥 Bot crashed due to: {e}", exc_info=True)
        time.sleep(5)
        sys.exit(1)

