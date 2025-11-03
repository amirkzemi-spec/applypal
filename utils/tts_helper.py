import os
import tempfile
import shutil
from openai import OpenAI
from pydub import AudioSegment

# -------------------------------------------------
# 🎧 Setup FFmpeg path dynamically (Render / Railway safe)
# -------------------------------------------------
ffmpeg_path = shutil.which("ffmpeg") or "/usr/local/bin/ffmpeg" or "/usr/bin/ffmpeg"
AudioSegment.converter = ffmpeg_path
print(f"🎬 Using FFmpeg at: {ffmpeg_path}")

# -------------------------------------------------
# 🔑 Initialize OpenAI client
# -------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------
# 🗣️ Main TTS function
# -------------------------------------------------
async def speak_reply(text: str) -> str:
    """
    Generate an OpenAI TTS voice file (OGG) and return its path for Telegram.
    If TTS or conversion fails, fall back to a short voice notice.
    """
    try:
        print("🎤 Generating TTS with OpenAI...")

        # Step 1️⃣ — Generate temporary MP3 file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",  # Voices: alloy, verse, sage, soft
                input=text[:400]  # Prevent overly long text
            )

            # Debug info for OpenAI response
            print(f"📦 TTS bytes: {len(response.content) if hasattr(response, 'content') else 'N/A'}")

            # Write bytes to file
            tmp_mp3.write(response.content)
            tmp_mp3.flush()
            tmp_mp3_path = tmp_mp3.name

        # Step 2️⃣ — Convert MP3 → OGG
        ogg_path = tmp_mp3_path.replace(".mp3", ".ogg")
        try:
            AudioSegment.from_mp3(tmp_mp3_path).export(ogg_path, format="ogg")
            print(f"✅ Voice file generated: {ogg_path} "
                  f"({os.path.getsize(ogg_path)/1024:.1f} KB)")
            print(f"🎧 Checking file existence: {os.path.exists(ogg_path)}")
            return ogg_path

        except Exception as conv_err:
            print(f"⚠️ Conversion failed: {conv_err}")
            raise RuntimeError("FFmpeg conversion failed")

    except Exception as e:
        # Step 3️⃣ — Fallback if TTS fails
        print(f"❌ TTS failed: {e}")
        import traceback; traceback.print_exc()
        return await _text_to_temp_voice_notice(text)

# -------------------------------------------------
# 🩹 Fallback voice helper
# -------------------------------------------------
async def _text_to_temp_voice_notice(_: str) -> str:
    """
    Creates a small OGG file saying “Voice unavailable — message sent as text”.
    """
    fallback_text = (
        "متاسفم، تولید صدا در این لحظه ممکن نیست. "
        "پاسخ به صورت متنی ارسال شد."
    )
    print("🔁 Falling back to text-only voice notice...")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=fallback_text
            )
            tmp_mp3.write(response.content)
            tmp_mp3.flush()
            tmp_mp3_path = tmp_mp3.name

        ogg_path = tmp_mp3_path.replace(".mp3", ".ogg")
        AudioSegment.from_mp3(tmp_mp3_path).export(ogg_path, format="ogg")
        print("✅ Fallback voice generated successfully.")
        return ogg_path

    except Exception as e:
        print(f"⚠️ Fallback TTS also failed: {e}")
        import traceback; traceback.print_exc()
        return None
