# bot_core/helpers_voice.py
import os, asyncio, subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment
from telegram import Update, InputFile
from telegram.ext import ContextTypes

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🎙️ Convert user voice → text
async def process_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg_file = await update.message.voice.get_file()
        await tg_file.download_to_drive("voice.ogg")

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

        # ✅ mark mode as voice
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
    try:
        await update.message.chat.send_action(action="typing")
        await asyncio.sleep(1.2)

        clean_text = text.strip()
        if len(clean_text) < 30 or clean_text.count(" ") < 4:
            print("💬 Short text detected — skipping voice.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return

        tts_input = clean_text[:1000]
        remaining = clean_text[1000:]

        print("🎤 Generating TTS with OpenAI...")
        mp3_path = Path("temp_voice.mp3")
        wav_path = Path("temp_voice.wav")
        ogg_path = Path("temp_voice.ogg")   # ✅ restored

        # --- Generate MP3 via OpenAI streaming
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=tts_input,
        ) as response:
            response.stream_to_file(mp3_path)

        if not mp3_path.exists() or mp3_path.stat().st_size < 2000:
            print("⚠️ Empty MP3 file — skipping voice.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return
        print(f"✅ MP3 size: {mp3_path.stat().st_size/1000:.1f} KB")

        # --- Convert MP3 → WAV (mono, 16 kHz)
        AudioSegment.from_file(mp3_path, format="mp3") \
            .set_frame_rate(16000).set_channels(1) \
            .export(wav_path, format="wav")

        # --- Use ffmpeg to ensure proper Opus OGG container (Telegram VOIP mode, higher quality)
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(wav_path),
            "-acodec", "libopus",
            "-b:a", "96k",            # ✅ higher bitrate for clearer speech
            "-ar", "16000",           # sample rate Telegram expects
            "-ac", "1",               # mono
            "-application", "voip",   # ✅ required for Telegram voice
            str(ogg_path)
        ], check=True)


        if not ogg_path.exists() or ogg_path.stat().st_size < 2000:
            print("⚠️ Empty OGG file — skipping voice.")
            await update.message.reply_text(clean_text, parse_mode="Markdown")
            return
        print(f"✅ OGG size: {ogg_path.stat().st_size/1000:.1f} KB")

        # --- Send to Telegram (test version keeps file)
        from telegram import InputFile

        with open(ogg_path, "rb") as voice_file:
            await update.message.chat.send_voice(
                voice=InputFile(voice_file, filename="voice.ogg"),
                caption="🎧 پاسخ صوتی از نیکا ویزا",
                parse_mode="Markdown",
            )

        print(f"✅ Voice sent successfully ({ogg_path.stat().st_size/1000:.1f} KB)")

        # --- keep OGG for manual playback test
        print("📂 Saved temp_voice.ogg for manual inspection — open it to verify sound.")

        # --- Optional cleanup (disabled for debugging)
        # for f in (mp3_path, wav_path, ogg_path):
        #     if Path(f).exists():
        #         os.remove(f)

        if remaining:
            await asyncio.sleep(1)
            await update.message.reply_text(remaining, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Error in speak_reply: {e}")
        await update.message.reply_text("⚠️ مشکلی در تولید پاسخ صوتی پیش آمد.")
