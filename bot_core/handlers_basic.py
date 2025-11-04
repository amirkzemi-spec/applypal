# bot_core/handlers_basic.py
import os
import random
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.tts_helper import speak_reply   # ✅ unified TTS function
from bot_core.onboarding_flow import process_onboarding
from bot_core.helpers_voice import process_voice
from utils.rag_helper_faiss_auto import RAGEngine

from user_tiers import check_user_limit, increment_user_query
from utils.referral_logic import check_referral_need

# -------------------------------------------------
# 🔐 Environment setup
# -------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
rag = RAGEngine()
# -------------------------------------------------
# 🏁 /start command (clean version)
# -------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send only one unified voice+caption greeting."""
    uid = update.message.from_user.id
    user_state = context.user_data
    user_state.clear()
    user_state.update({"stage": "ask_name", "mode": "text"})

    # 🎓 One greeting message (caption + voice)
    intro_caption = (
        "🎓 به نیکا ویزا خوش اومدی! من یه مشاور هوشمندم برای کمک به تحصیل، ویزا و بورسیه‌ها.\n\n"
        "👋 حالا بگو اسمت چیه؟"
    )

    try:
        # Generate & send unified voice greeting
        voice_path = await speak_reply(intro_caption)
        if voice_path and os.path.exists(voice_path):
            await update.message.reply_voice(
                voice=open(voice_path, "rb"),
                caption=intro_caption,
                parse_mode="Markdown",
            )
            print(f"✅ Voice intro sent ({os.path.getsize(voice_path)/1024:.1f} KB)")
        else:
            print("⚠️ No voice generated, sending fallback text.")
            await update.message.reply_text(intro_caption, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Voice intro failed: {e}")
        await update.message.reply_text(intro_caption, parse_mode="Markdown")


# -------------------------------------------------
# 💬 Handle text messages
# -------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE, override_text=None):
    """Main text handler — ensures only ONE reply per message (voice + caption)."""
    uid = update.message.from_user.id
    user_state = context.user_data
    text = override_text or (update.message.text.strip() if update.message.text else "")

    if not text:
        await update.message.reply_text("⚠️ لطفاً دوباره تلاش کنید.")
        return

    # 🧠 Developer bypass + tier check
    ok, msg = check_user_limit(uid)
    if not ok:
        await update.message.reply_text(msg)
        return
    if msg:
        # e.g., reminder for subscription
        await update.message.reply_text(msg)

    increment_user_query(uid)

    # 🧩 Process onboarding and get AI recommendation
    reply_text = await process_onboarding(update, context, uid, text, user_state)
    if not reply_text:
        print("⚠️ No reply_text returned from process_onboarding.")
        return

    # 🧱 Guard: prevent duplication
    reply_text = reply_text.strip()
    if not reply_text:
        return

    # 🚫 Skip TTS for long text
    if len(reply_text) > 900:
        await update.message.reply_text("🗣️ پاسخ طولانی است — به صورت متنی ارسال شد:")
        await update.message.reply_text(reply_text)
        return

    # 🎧 Generate and send one unified voice+caption reply
    try:
        print("🎤 Generating voice reply …")
        voice_path = await speak_reply(reply_text)

        if voice_path and os.path.exists(voice_path):
            size_kb = os.path.getsize(voice_path) / 1024
            await update.message.reply_voice(
                voice=open(voice_path, "rb"),
                caption=reply_text,
                parse_mode="Markdown"
            )
            print(f"✅ Voice reply sent ({size_kb:.1f} KB)")
        else:
            print("⚠️ No voice generated — sending text fallback.")
            await update.message.reply_text(reply_text, parse_mode="Markdown")

    except Exception as e:
        import traceback
        print(f"❌ Voice generation error: {e}")
        traceback.print_exc()
        await update.message.reply_text(reply_text, parse_mode="Markdown")


# -------------------------------------------------
# 🎙 Handle user voice input
# -------------------------------------------------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe incoming voice and forward to handle_text."""
    try:
        await process_voice(update, context)
    except Exception as e:
        print(f"❌ Error in handle_voice: {e}")
        await update.message.reply_text("⚠️ خطا در پردازش پیام صوتی شما.")


# -------------------------------------------------
# 🎓 Ask study level (inline buttons)
# -------------------------------------------------
async def ask_study_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user for their last education level."""
    keyboard = [
        [InlineKeyboardButton("🎓 دیپلم دبیرستان دارم", callback_data="study_highschool")],
        [InlineKeyboardButton("🎓 مدرک کارشناسی دارم", callback_data="study_bachelor")],
        [InlineKeyboardButton("🎓 مدرک کارشناسی ارشد دارم", callback_data="study_master")],
        [InlineKeyboardButton("🎓 مدرک دکترا دارم", callback_data="study_phd")],
    ]
    await update.message.reply_text(
        "🎓 آخرین مدرک تحصیلی شما چیست؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------------------------------------------------
# 🌍 Ask preferred country (inline buttons)
# -------------------------------------------------
async def ask_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user for their target country."""
    keyboard = [
        [
            InlineKeyboardButton("🇨🇦 کانادا", callback_data="country_Canada"),
            InlineKeyboardButton("🇬🇧 بریتانیا", callback_data="country_UK"),
        ],
        [
            InlineKeyboardButton("🇩🇪 آلمان", callback_data="country_Germany"),
            InlineKeyboardButton("🇮🇹 ایتالیا", callback_data="country_Italy"),
        ],
        [
            InlineKeyboardButton("🇺🇸 آمریکا", callback_data="country_USA"),
            InlineKeyboardButton("🇳🇱 هلند", callback_data="country_Netherlands"),
        ],
        [
            InlineKeyboardButton("🇸🇪 سوئد", callback_data="country_Sweden"),
            InlineKeyboardButton("🌍 سایر کشورها", callback_data="country_other"),
        ],
    ]
    await update.message.reply_text(
        "🌍 علاقه‌مند به تحصیل در کدام کشور هستید؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
# in bot_core/handlers_tiers.py or handlers_basic.py

from user_tiers import get_user_count, get_active_users_today

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = int(os.getenv("ADMIN_ID", "0"))
    if update.message.from_user.id != admin_id:
        await update.message.reply_text("⛔️ فقط مدیر می‌تواند آمار را ببیند.")
        return

    total_users = get_user_count()
    active_today = get_active_users_today()

    await update.message.reply_text(
        f"📊 آمار نیکا ویزا:\n\n"
        f"👥 تعداد کل کاربران: {total_users}\n"
        f"🔥 کاربران فعال امروز: {active_today}"
    )
