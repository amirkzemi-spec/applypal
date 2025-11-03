import os
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -------------------------------
# 🔐 Environment & Setup
# -------------------------------
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()
    print("📦 Local .env loaded.")
else:
    print("☁️ Running on Railway — env vars loaded automatically.")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN missing — check Railway Variables tab")
if not OPENAI_KEY:
    print("⚠️ OPENAI_API_KEY missing — GPT or voice features may fail")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

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
from bot_core.handlers_tiers import upgrade, handle_receipt, admin_approve

# -------------------------------
# 🎓 Inline button callbacks
# -------------------------------
async def study_level_callback(update, context: ContextTypes.DEFAULT_TYPE):
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


async def country_callback(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected = query.data.split("_")[1]
    context.user_data["preferred_country"] = selected
    await query.message.reply_text(
        f"🌍 کشور انتخابی شما: {selected}. لطفاً سطح زبان یا نمره آیلتس خود را بنویسید."
    )

# -------------------------------
# 🤖 Bot Runner with Auto-Restart
# -------------------------------
def run_bot():
    """Run the bot and restart automatically if it crashes."""
    retry_delay = 5  # seconds before retry
    while True:
        try:
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

            # --- Message Handlers ---
            app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
            app.add_handler(MessageHandler(filters.VOICE, handle_voice))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

            # --- Inline Button Callbacks ---
            app.add_handler(CallbackQueryHandler(study_level_callback, pattern="^study_"))
            app.add_handler(CallbackQueryHandler(country_callback, pattern="^country_"))

            logging.info("🤖 Nika Visa Bot started successfully!")
            app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)

        except Exception as e:
            logging.error(f"💥 Bot crashed due to: {e}")
            logging.info(f"⏳ Restarting in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue

# -------------------------------
# 🏁 Entry Point
# -------------------------------
if __name__ == "__main__":
    try:
        run_bot()
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped manually.")
