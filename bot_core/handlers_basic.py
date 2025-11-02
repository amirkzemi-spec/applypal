# bot_core/handlers_basic.py
import os
import random
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from user_tiers import check_user_limit, increment_user_query
from utils.referral_logic import check_referral_need
from utils.rag_helper_faiss_auto import RAGEngine
rag = RAGEngine()   # create a global engine instance
from bot_core.onboarding_flow import process_onboarding
from bot_core.helpers_voice import process_voice, speak_reply

# -------------------------------------------------
# 🔐 Environment setup
# -------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
user_data = {}

# -------------------------------------------------
# 🏁 Start command
# -------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_state = context.user_data   # ✅ persistent dict for this user

    # Initialize user session if first time
    if "stage" not in user_state:
        user_state["stage"] = "ask_name"
        user_state["mode"] = "text"

    intro_texts = [
        "👋 سلام! من دستیار هوش مصنوعی نیکا ویزا هستم...",
        "🎓 به نیکا ویزا خوش اومدی!...",
        "🤖 سلام! من دستیار هوش مصنوعی نیکا ویزا هستم..."
    ]
    chosen_intro = random.choice(intro_texts)
    await update.message.reply_text(chosen_intro)

    from bot_core.helpers_voice import speak_reply
    await speak_reply(update, "سلام! من نیکا ویزا هستم. سنت و مدرک تحصیلی‌ات رو بگو.")
    await update.message.reply_text("👋 حالا بگو اسمت چیه؟")


# -------------------------------------------------
# 💬 Handle text
# -------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE, override_text=None):
    uid = update.message.from_user.id
    user_state = context.user_data  # ✅ each user has persistent dict

    text = override_text or (update.message.text.strip() if update.message.text else "")
    if not text:
        await update.message.reply_text("⚠️ لطفاً دوباره تلاش کنید.")
        return

    # ✅ Check usage limits (from user_tiers)
    from user_tiers import check_user_limit, increment_user_query
    ok, msg = check_user_limit(uid)
    if not ok:
        await update.message.reply_text(msg)
        return
    increment_user_query(uid)

    # ✅ Process onboarding and get AI reply
    from bot_core.onboarding_flow import process_onboarding
    reply_text = await process_onboarding(update, context, uid, text, user_state)

    # -------------------------------------------------
    # 🧠 New safeguard: skip TTS if reply too long
    # -------------------------------------------------
    if not reply_text:
        return

    if len(reply_text) > 800:
        await update.message.reply_text("🗣️ پاسخ طولانی است — به صورت متنی ارسال شد:")
        await update.message.reply_text(reply_text)
        return

    # -------------------------------------------------
    # 🎧 Generate and send voice reply (TTS)
    # -------------------------------------------------
    try:
        from utils.tts_helper import speak_reply  # adjust import if needed
        voice_path = await speak_reply(reply_text)
        await update.message.reply_voice(voice=open(voice_path, "rb"))
    except Exception as e:
        print(f"❌ Error in speak_reply: {e}")
        await update.message.reply_text(reply_text)



# -------------------------------------------------
# 🎙 Handle voice
# -------------------------------------------------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot_core.helpers_voice import process_voice
    await process_voice(update, context)

# -------------------------------------------------
# 🎓 Ask study level (inline buttons)
# -------------------------------------------------
async def ask_study_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎓 دیپلم دبیرستان دارم", callback_data="study_highschool")],
        [InlineKeyboardButton("🎓 مدرک کارشناسی دارم", callback_data="study_bachelor")],
        [InlineKeyboardButton("🎓 مدرک کارشناسی ارشد دارم", callback_data="study_master")],
        [InlineKeyboardButton("🎓 مدرک دکترا دارم", callback_data="study_phd")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎓 آخرین مدرک تحصیلی شما چیست؟", reply_markup=reply_markup)

# -------------------------------------------------
# 🌍 Ask preferred country (inline buttons)
# -------------------------------------------------
async def ask_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌍 علاقه‌مند به تحصیل در کدام کشور هستید؟", reply_markup=reply_markup)
