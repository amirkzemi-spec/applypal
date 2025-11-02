# bot_core/helpers_voice.py
import os, asyncio, subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InputFile
from telegram.ext import ContextTypes

# ---------------------------------------
# 🧩 Optional import guard for Railway
# ---------------------------------------
try:
    from pydub import AudioSegment
except Exception as e:
    print("⚠️ Audio library not fully available:", e)
    AudioSegment = None

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------------------------------------
# 🎙️ Convert user voice → text
# -----------------------------------------------------------
async def process_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe user voice messages to text and forward to text handler."""
    try:
        tg_file = await update.message.voice.get_file()
        await tg_file.download_to_drive("voice.ogg")

        if not AudioSegment:
            await update.message.reply_text("🔇 ماژول صوتی در این سرور فعال نیست.")
            return

        AudioSegment.from_file("voice.ogg").export("voice.wav", format="wav")

        with open("voice.wav", "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio,
            )

        text = getattr(transcript, "text", "").strip()
        if not text:
            await update.message.reply_text("⚠️ صدای شما واضح نبود.")
            return

        print(f"🎙️ گفتار کاربر: {text}")
        context.user_data["mode"] = "voice"

        from bot_core.handlers_basic import handle_text
        await handle_text(update, context, override_text=text)

    except Exception as e:
        print("❌ خطا در پردازش صوت:", e)
        await update.message.reply_text("⚠️ خطا در پردازش صوت.")

# -----------------------------------------------------------
# 🎧 Convert AI text → voice and send as Telegram message
# -----------------------------------------------------------
async def speak_reply(update, text: str):
    """Generate TTS reply and send as Telegram voice message (Railway-safe)."""
    try:
        await update.message.chat.send_action(action="typing")
        await asyncio.sleep(1.2)

        clean_text = text.strip()
        if len(clean_text) < 30 or clean_text.count(" ") < 4:
            print("💬 Short text detected — skipping voice.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return

        # 🧭 Detect if running on Railway
        is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
        if is_railway:
            print("🚀 Detected Railway environment — skipping voice generation.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return

        # 🧠 Generate TTS (MP3)
        print("🎤 Generating TTS with OpenAI...")
        mp3_path = Path("temp_voice.mp3")
        wav_path = Path("temp_voice.wav")
        ogg_path = Path("temp_voice.ogg")

        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=clean_text[:1000],
        ) as response:
            response.stream_to_file(mp3_path)

        # Verify MP3
        if not mp3_path.exists() or mp3_path.stat().st_size < 2000:
            print("⚠️ Empty MP3 file — skipping voice.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return
        print(f"✅ MP3 size: {mp3_path.stat().st_size/1000:.1f} KB")

        # Ensure pydub is available
        if not AudioSegment:
            print("⚠️ Audio library not available — skipping ffmpeg conversion.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return

        # Convert MP3 → WAV → OGG
        AudioSegment.from_file(mp3_path, format="mp3") \
            .set_frame_rate(16000).set_channels(1) \
            .export(wav_path, format="wav")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(wav_path),
            "-acodec", "libopus",
            "-b:a", "96k",
            "-ar", "16000",
            "-ac", "1",
            "-application", "voip",
            str(ogg_path)
        ], check=True)

        # Verify OGG
        if not ogg_path.exists() or ogg_path.stat().st_size < 2000:
            print("⚠️ Empty OGG file — skipping voice.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return
        print(f"✅ OGG size: {ogg_path.stat().st_size/1000:.1f} KB")

        # Send voice
        with open(ogg_path, "rb") as voice_file:
            await update.message.chat.send_voice(
                voice=InputFile(voice_file, filename="voice.ogg"),
                caption="🎧 پاسخ صوتی از نیکا ویزا",
                parse_mode="Markdown",
            )

        print(f"✅ Voice sent successfully ({ogg_path.stat().st_size/1000:.1f} KB)")
        print("📂 Saved temp_voice.ogg for manual inspection — open it to verify sound.")

    except Exception as e:
        print(f"❌ Error in speak_reply: {e}")
        await update.message.reply_text("⚠️ مشکلی در تولید پاسخ صوتی پیش آمد.")
