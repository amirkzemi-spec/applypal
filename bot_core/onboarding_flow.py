import os
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from utils.referral_logic import check_referral_need
from utils.rag_helper_faiss_auto import RAGEngine
from utils.user_logs import save_log
from utils.constraint_filter import filter_countries
from utils.tts_helper import speak_reply  # ✅ Working async TTS helper

# -----------------------------
# 🔐 Environment & RAG setup
# -----------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
rag = RAGEngine()


# -----------------------------
# 🌍 Detection Helpers
# -----------------------------
def detect_country(text: str):
    mapping = {
        "netherlands": "Netherlands",
        "germany": "Germany",
        "switzerland": "Switzerland",
        "italy": "Italy",
        "canada": "Canada",
        "usa": "USA",
        "united kingdom": "United Kingdom",
        "uk": "United Kingdom",
    }
    for k, v in mapping.items():
        if k in text.lower():
            return v
    return None


def detect_category(text: str):
    cats = {
        "visa": "visa",
        "scholar": "scholarship",
        "fund": "funding",
        "tuition": "tuition",
        "work": "work",
        "residen": "residence",
        "study": "study",
        "admiss": "admission",
        "permit": "visa",
    }
    text_low = text.lower()
    for k, v in cats.items():
        if k in text_low:
            return v
    return None


# -----------------------------
# 💡 Generate Recommendation
# -----------------------------
async def generate_recommendation(update: Update, summary: str, name: str, country: str = None, user_data: dict = None):
    """Generate personalized study recommendations using RAG + GPT and send one unified reply."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown_user"

    # 🔍 Detect context
    detected_country = detect_country(summary) or country
    detected_category = detect_category(summary)

    # ⚖️ Constraint filters
    profile = {
        "budget": user_data.get("budget_max") if user_data else 0,
        "ielts": user_data.get("ielts", 0),
        "age": user_data.get("age", 0),
    }
    limited_countries = filter_countries(profile)
    if not detected_country and limited_countries:
        detected_country = limited_countries[0]

    # 🔎 RAG search
    ctx = rag.search(
        query=summary,
        top_k=3,
        country=detected_country,
        category=detected_category,
    )
    print(f"🔍 Auto-detected: country={detected_country}, category={detected_category}")
    print(f"🎯 Constraint-filtered options: {limited_countries}")

    # 🧠 Build GPT prompt
    prompt = f"""
تو یک مشاور تحصیلی هوشمند به نام نیکا ویزا هستی.

🧾 اطلاعات دانشجو:
{summary}

📚 داده‌های پایگاه دانش:
{ctx}

🎯 دستورالعمل:
- فقط ۱ تا ۲ کشور مناسب کاربر را پیشنهاد بده.
- اگر بودجه یا آیلتس پایین است، کشورهایی با شرایط سخت‌تر را حذف کن.
- پاسخ کوتاه، کاربردی و زیر ۱۵۰ کلمه باشد.
    """

    # 🤖 Generate GPT response
    print("🤖 Generating recommendation via GPT-4o-mini...")
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert educational consultant named Nika Visa."},
            {"role": "user", "content": prompt},
        ],
    )

    advice = (completion.choices[0].message.content or "").strip() or "پاسخی از هوش مصنوعی دریافت نشد."

    # 💬 Referral link if needed
    if check_referral_need(summary):
        advice += "\n\n💬 برای مشاوره ویزا و اقدام رسمی، با [نیکا ویزا](https://t.me/nikavisa_admin) تماس بگیرید."

    # 🧾 Save query log
    save_log(
        user_id=user_id,
        username=username,
        query=summary,
        country=detected_country,
        category=detected_category,
    )

    # 🎤 Voice + caption unified reply
    try:
        print("🎤 Calling speak_reply() …")
        voice_path = await speak_reply(advice)
        if voice_path and os.path.exists(voice_path):
            await update.message.reply_voice(
                voice=open(voice_path, "rb"),
                caption=advice,
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(advice, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Voice generation failed: {e}")
        await update.message.reply_text(advice, parse_mode="Markdown")


# -----------------------------
# 🧭 Onboarding Flow (cleaned)
# -----------------------------
async def process_onboarding(update, context, uid, text, user_data):
    """Main onboarding flow controller."""
    stage = user_data.get("stage", "ask_name")

    # 🧩 Skip onboarding if it’s the greeting step
    if text.lower().startswith("/start"):
        return

    # Stage 1️⃣ — Name
    if stage == "ask_name":
        user_data["name"] = text.split()[0].capitalize()
        user_data["stage"] = "ask_age"
        await update.message.reply_text(f"خوش اومدی {user_data['name']} 👋 چند سالته؟")
        return

    # Stage 2️⃣ — Age
    elif stage == "ask_age":
        user_data["age"] = text
        user_data["stage"] = "ask_study"
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("🎓 دیپلم دارم", callback_data="study_highschool")],
            [InlineKeyboardButton("🎓 کارشناسی دارم", callback_data="study_bachelor")],
            [InlineKeyboardButton("🎓 ارشد دارم", callback_data="study_master")],
            [InlineKeyboardButton("🎓 دکترا دارم", callback_data="study_phd")],
        ]
        await update.message.reply_text(
            "🎓 آخرین مدرک تحصیلی شما چیست؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Stage 3️⃣ — Education
    elif stage == "ask_study":
        user_data["study"] = text
        user_data["stage"] = "ask_future_program"
        await update.message.reply_text("🎯 در چه رشته‌ای قصد ادامه تحصیل داری؟")
        return

    # Stage 4️⃣ — Desired program
    elif stage == "ask_future_program":
        user_data["future_program"] = text
        user_data["stage"] = "ask_budget"
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        keyboard = [
            [KeyboardButton("💸 ۰ تا ۵۰۰۰ دلار"), KeyboardButton("💰 ۵۰۰۰ تا ۱۰۰۰۰ دلار")],
            [KeyboardButton("💼 ۱۰۰۰۰ تا ۲۰۰۰۰ دلار"), KeyboardButton("🌍 بیش از ۲۰۰۰۰ دلار")],
        ]
        await update.message.reply_text(
            "💰 بودجه‌ی سالیانه‌ات برای تحصیل چقدره؟",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )
        return

    # Stage 5️⃣ — Budget
    elif stage == "ask_budget":
        user_data["budget_label"] = text
        choice = text.replace(" ", "")
        if "۰" in choice and "۵" in choice:
            user_data["budget_min"], user_data["budget_max"] = 0, 5000
        elif "۵" in choice and "۱۰" in choice:
            user_data["budget_min"], user_data["budget_max"] = 5000, 10000
        elif "۱۰" in choice and "۲۰" in choice:
            user_data["budget_min"], user_data["budget_max"] = 10000, 20000
        else:
            user_data["budget_min"], user_data["budget_max"] = 20000, 999999
        user_data["stage"] = "ask_goal"
        from bot_core.handlers_basic import ask_country
        await ask_country(update, context)
        return

    # Stage 6️⃣ — Country
    elif stage == "ask_goal":
        user_data["goal_country"] = text
        user_data["stage"] = "complete"
        profile = user_data
        summary = (
            f"نام: {profile['name']}, سن: {profile['age']}, "
            f"مدرک: {profile['study']}, رشته: {profile['future_program']}, "
            f"بودجه: {profile['budget_label']} "
            f"(بین {profile['budget_min']} تا {profile['budget_max']} دلار)، "
            f"کشور: {profile['goal_country']}"
        )
        await update.message.reply_text("✅ در حال بررسی بهترین گزینه‌ها برای شما هستم...")
        await generate_recommendation(update, summary, profile["name"], profile["goal_country"], user_data)
        return

    # Stage ✅ — Completed
    elif stage == "complete":
        await continue_chat(update, text, uid, user_data)
        return


# -----------------------------
# 💬 Continue Chat (fixed unified reply)
# -----------------------------
async def continue_chat(update, text, uid, user_data):
    """Handles free chat after onboarding — sends a single unified reply."""
    profile_summary = (
        f"نام: {user_data.get('name','')}، سن: {user_data.get('age','')}، "
        f"مدرک: {user_data.get('study','')}، "
        f"رشته هدف: {user_data.get('future_program','')}، "
        f"بودجه: {user_data.get('budget_label','')}، "
        f"کشور: {user_data.get('goal_country','')}"
    )

    history = user_data.setdefault("chat_history", [])
    history.append({"role": "user", "content": text})
    history = history[-5:]

    ctx = (
        "تو مشاور تحصیلی نیکا ویزا هستی و گفت‌وگو را بر اساس اطلاعات قبلی ادامه می‌دهی.\n\n"
        f"🧾 اطلاعات کاربر:\n{profile_summary}\n\n"
        "سؤال جدید کاربر:"
    )

    messages = [{"role": "system", "content": ctx}] + history
    completion = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    reply = completion.choices[0].message.content.strip()

    history.append({"role": "assistant", "content": reply})
    user_data["chat_history"] = history

    # 🎤 Unified reply (voice + caption)
    try:
        voice_path = await speak_reply(reply)
        if voice_path and os.path.exists(voice_path):
            await update.message.reply_voice(
                voice=open(voice_path, "rb"),
                caption=reply,
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Voice generation failed in continue_chat: {e}")
        await update.message.reply_text(reply, parse_mode="Markdown")

    # Return reply for consistency/logging
    return reply
