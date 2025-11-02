# main.py
import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -------------------------------
# 🔐 Environment & Database Setup
# -------------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN not found in .env")
if not OPENAI_KEY:
    print("⚠️ Warning: OPENAI_API_KEY not found — voice replies will fail.")

# Initialize DBs
from user_tiers import init_db as init_tiers_db
from utils.user_logs import init_db as init_logs_db
init_tiers_db()
init_logs_db()
print("✅ Environment loaded successfully.")

# 🧩 Core Handlers
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
# 🤖 Main Bot Runner
# -------------------------------
def main():
    """Start the Telegram bot using ApplicationBuilder (PTB v20+)."""
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .arbitrary_callback_data(True)
        .build()
    )

    # --- Command Handlers ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upgrade", upgrade))

    # --- Message Handlers ---
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # --- Inline Callbacks ---
    app.add_handler(CallbackQueryHandler(study_level_callback, pattern="^study_"))
    app.add_handler(CallbackQueryHandler(country_callback, pattern="^country_"))

    # --- Admin Commands ---
    app.add_handler(CommandHandler("approve", admin_approve))

    print("🤖 ربات نیکا ویزا با موفقیت اجرا شد...")

    try:
        app.run_polling(stop_signals=None)
    except Exception as e:
        print(f"❌ Unexpected error while running bot: {e}")
    finally:
        print("🛑 Bot stopped.")


# -------------------------------
# 🏁 Entry Point
# -------------------------------
if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped manually.")
