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
from user_tiers import init_db
from utils.user_logs import init_db
from utils.user_logs import init_db

# 🧩 Core handlers
from bot_core.handlers_basic import start, handle_text, handle_voice
from bot_core.handlers_tiers import upgrade, handle_receipt, admin_approve

# -------------------------------
# 🔐 Load environment & init DB
# -------------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN not found in .env")

# ✅ Initialize local user logs database
from utils.user_logs import init_db
init_db()  # <-- This line runs once at startup

# -------------------------------
# 🤖 Main bot runner
# -------------------------------
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .build()
    )

# -------------------------------
# 🔐 Load environment & init DB
# -------------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN not found in .env")

# ✅ Initialize local user logs database
from utils.user_logs import init_db
init_db()

# -------------------------------
# 🤖 Main bot runner
# -------------------------------
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .build()
    )

# -------------------------------
# 🔐 Load environment & init DB
# -------------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN not found in .env")
if not OPENAI_KEY:
    print("⚠️ Warning: OPENAI_API_KEY not found — voice replies will fail.")

init_db()
print("✅ Environment loaded successfully.")


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
# 🤖 Main bot runner
# -------------------------------
def main():
    app = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .read_timeout(60)
    .write_timeout(60)
    .connect_timeout(30)
    .arbitrary_callback_data(True)    # optional safety
    .build()
)


    # --- Commands ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upgrade", upgrade))

    # --- Messages ---
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # --- Inline buttons ---
    app.add_handler(CallbackQueryHandler(study_level_callback, pattern="^study_"))
    app.add_handler(CallbackQueryHandler(country_callback, pattern="^country_"))

    # --- Admin ---
    app.add_handler(MessageHandler(filters.COMMAND, admin_approve))

    print("🤖 ربات نیکا ویزا با موفقیت اجرا شد...")
    try:
        app.run_polling(stop_signals=None)
    except Exception as e:
        print(f"❌ Unexpected error while running bot: {e}")
    finally:
        print("🛑 Bot stopped.")


# -------------------------------
# 🏁 Entry point
# -------------------------------
if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped manually.")
