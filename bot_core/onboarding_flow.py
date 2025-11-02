# bot_core/onboarding_flow.py
import os
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from bot_core.helpers_voice import speak_reply
from utils.referral_logic import check_referral_need
from utils.rag_helper_faiss_auto import RAGEngine
from utils.user_logs import save_log
from utils.constraint_filter import filter_countries   # 👈 add this
rag = RAGEngine()

# 🔐 Load environment
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# Simple keyword-based detectors
# -----------------------------
def detect_country(text):
    mapping = {
        "netherlands": "Netherlands",
        "germany": "Germany",
        "switzerland": "Switzerland",
        "italy": "Italy",
        "canada": "Canada",
        "usa": "USA",
        "united kingdom": "United Kingdom",
        "uk": "United Kingdom",
        "sweden": "Sweden",
        "finland": "Finland",
        "norway": "Norway",
        "austria": "Austria",
        "france": "France"
    }
    text_low = text.lower()
    for k, v in mapping.items():
        if k in text_low:
            return v
    return None


def detect_category(text):
    cats = {
        "visa": "visa",
        "scholar": "scholarship",
        "fund": "funding",
        "tuition": "tuition",
        "work": "work",
        "residen": "residence",
        "study": "study",
        "admiss": "admission",
        "permit": "visa"
    }
    text_low = text.lower()
    for k, v in cats.items():
        if k in text_low:
            return v
    return None


# -------------------- Recommendation with RAG Context --------------------
async def generate_recommendation(update, summary: str, name: str, country: str = None, user_data: dict = None):
    """Generate personalized study recommendations based on user data and RAG knowledge."""

    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown_user"

    # 🔍 Detect country & category
    detected_country = detect_country(summary) or country
    detected_category = detect_category(summary)

    # ⚖️ Apply constraints if user data exists
    profile = {
        "budget": user_data.get("budget_max") if user_data else 0,
        "ielts": user_data.get("ielts", 0),
        "age": user_data.get("age", 0),
    }
    limited_countries = filter_countries(profile)

    if not detected_country and limited_countries:
        detected_country = limited_countries[0]

    # 🔎 Search RAG
    ctx = rag.search(
        query=summary,
        top_k=3,
        country=detected_country,
        category=detected_category
    )

    print(f"🔍 Auto-detected: country={detected_country}, category={detected_category}")
    print(f"🎯 Constraint-filtered options: {limited_countries}")

    # 🧠 Build GPT prompt
    prompt = f"""
تو یک مشاور تحصیلی هوشمند و واقعی به نام نیکا ویزا هستی.
از اطلاعات زیر برای مشاوره استفاده کن:

🧾 اطلاعات دانشجو:
{summary}

📚 داده‌های پایگاه دانش (منابع واقعی):
{ctx}

🎯 دستورالعمل:
- فقط ۱ تا ۲ کشور را که واقعا مناسب کاربر هستند پیشنهاد بده.
- اگر بودجه یا آیلتس پایین است، کشورهایی را حذف کن که شرایط سخت‌تری دارند.
- توضیح بده چرا کشورهایی را توصیه می‌کنی یا رد می‌کنی.
- پاسخ کوتاه، کاربردی و زیر ۱۵۰ کلمه باشد.
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert educational consultant named Nika Visa."},
            {"role": "user", "content": prompt},
        ],
    )

    advice = completion.choices[0].message.content.strip() or "پاسخی از هوش مصنوعی دریافت نشد."

    # 💬 Referral if necessary
    if check_referral_need(summary):
        advice += "\n\n💬 برای مشاوره ویزا و اقدام رسمی، با [نیکا ویزا](https://t.me/nikavisa_admin) تماس بگیرید."

    # 🧾 Save log (query + detected info)
    save_log(
        user_id=user_id,
        username=username,
        query=summary,
        country=detected_country,
        category=detected_category
    )

    # 🗣️ Send + speak
    await update.message.reply_text(advice, parse_mode="Markdown")
    await asyncio.sleep(1.5)
    await speak_reply(update, advice)


# -------------------- Onboarding Process --------------------
async def process_onboarding(update, context, uid, text, user_data):
    # user_data is already per-user persistent dict

    if user_data.get("stage") == "complete":
        from bot_core.onboarding_flow import continue_chat
        await continue_chat(update, text, uid, user_data)
        return

    stage = user_data.get("stage", "ask_name")

    # Fast-track (free text)
    if len(text.split()) > 5 and stage == "ask_name":
        await update.message.reply_text("✅ در حال بررسی اطلاعات شما هستم...")
        summary = f"پیام کاربر: {text}"
        await generate_recommendation(update, summary, "کاربر", user_data=user_data)
        return

    # --- Stage: Name
    if stage == "ask_name":
        user_data["name"] = text.split()[0].capitalize()
        user_data["stage"] = "ask_age"
        await update.message.reply_text(f"خوش‌اومدی {user_data['name']} 👋 چند سالته؟")
        return

    # --- Stage: Age
    elif stage == "ask_age":
        user_data["age"] = text
        user_data["stage"] = "ask_study"

        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("🎓 دیپلم دبیرستان دارم", callback_data="study_highschool")],
            [InlineKeyboardButton("🎓 مدرک کارشناسی دارم", callback_data="study_bachelor")],
            [InlineKeyboardButton("🎓 مدرک کارشناسی ارشد دارم", callback_data="study_master")],
            [InlineKeyboardButton("🎓 مدرک دکترا دارم", callback_data="study_phd")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🎓 آخرین مدرک تحصیلی شما چیست؟", reply_markup=reply_markup)
        return

    # --- Stage: Education
    elif stage == "ask_study":
        user_data["study"] = text
        user_data["stage"] = "ask_future_program"
        await update.message.reply_text("🎯 در چه رشته‌ای قصد ادامه تحصیل داری؟")
        return

    # --- Stage: Desired program
    elif stage == "ask_future_program":
        user_data["future_program"] = text
        user_data["stage"] = "ask_budget"

        keyboard = [
            [KeyboardButton("💸 ۰ تا ۵۰۰۰ دلار"), KeyboardButton("💰 ۵۰۰۰ تا ۱۰۰۰۰ دلار")],
            [KeyboardButton("💼 ۱۰۰۰۰ تا ۲۰۰۰۰ دلار"), KeyboardButton("🌍 بیش از ۲۰۰۰۰ دلار")],
        ]
        await update.message.reply_text(
            "💰 بودجه سالیانه‌ی شما برای تحصیل چقدر است؟",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )
        return

    # --- Stage: Budget
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

    # --- Stage: Country preference
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

    elif stage == "complete":
        await continue_chat(update, text, uid, user_data)


# -------------------- Continue Chat Mode --------------------
async def continue_chat(update, text, uid, user_data):
    profile = {
        "name": user_data.get("name", ""),
        "age": user_data.get("age", ""),
        "study": user_data.get("study", ""),
        "future_program": user_data.get("future_program", ""),
        "budget_label": user_data.get("budget_label", ""),
        "goal_country": user_data.get("goal_country", ""),
    }

    profile_summary = (
        f"نام: {profile['name']}، سن: {profile['age']}، "
        f"مدرک تحصیلی: {profile['study']}، "
        f"رشته هدف: {profile['future_program']}، "
        f"بودجه: {profile['budget_label']}، "
        f"کشور مورد علاقه: {profile['goal_country']}"
    )

    history = user_data.setdefault("chat_history", [])
    history.append({"role": "user", "content": text})
    history = history[-5:]

    ctx = (
        "تو مشاور تحصیلی نیکا ویزا هستی. "
        "پاسخ‌هات را بر اساس شرایط قبلی کاربر بده و گفت‌وگو را پیوسته نگه دار.\n\n"
        f"🧾 اطلاعات ثبت‌شده‌ی کاربر:\n{profile_summary}\n\n"
        "در ادامه، کاربر سؤالات جدیدی می‌پرسد:"
    )

    messages = [{"role": "system", "content": ctx}] + history

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    reply = completion.choices[0].message.content.strip()

    history.append({"role": "assistant", "content": reply})
    user_data["chat_history"] = history

    await update.message.reply_text(reply, parse_mode="Markdown")

    if user_data.get("mode") == "voice":
        await speak_reply(update, reply)
