import os
import tempfile
from openai import OpenAI
from pydub import AudioSegment

# -------------------------------------------------
# 🎧 Setup FFmpeg for Render
# -------------------------------------------------
# Render places ffmpeg in /usr/bin, so we tell Pydub explicitly
AudioSegment.converter = "/usr/bin/ffmpeg"

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -------------------------------------------------
# 🗣️ TTS Generator with Auto-Fallback
# -------------------------------------------------
async def speak_reply(text: str) -> str:
    """
    Generate an OpenAI TTS voice file and return its OGG path for Telegram.
    If TTS fails, return a plain text message as a backup.
    """
    try:
        print("🎤 Generating TTS with OpenAI...")

        # Step 1. Generate MP3 using OpenAI
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",  # other options: "verse", "sage", "soft"
                input=text[:400]  # limit length to avoid token overflow
            )
            tmp_mp3.write(response.content)
            tmp_mp3.flush()

        # Step 2. Convert MP3 → OGG for Telegram
        ogg_path = tmp_mp3.name.replace(".mp3", ".ogg")

        try:
            AudioSegment.from_mp3(tmp_mp3.name).export(ogg_path, format="ogg")
            print(f"✅ Voice generated successfully ({os.path.getsize(tmp_mp3.name)/1024:.1f} KB)")
            return ogg_path

        except Exception as conv_err:
            print(f"⚠️ Conversion failed: {conv_err}")
            raise RuntimeError("FFmpeg conversion failed")

    except Exception as e:
        # Step 3. Auto-fallback to text if any part fails
        print(f"❌ TTS failed: {e}")
        fallback_path = await _text_to_temp_voice_notice(text)
        return fallback_path


# -------------------------------------------------
# 🩹 Fallback helper — generates a temporary OGG file saying “text only”
# -------------------------------------------------
async def _text_to_temp_voice_notice(text: str) -> str:
    """
    Creates a small OGG file telling user that voice is unavailable,
    and includes part of the text for continuity.
    """
    fallback_text = (
        "متاسفم، تولید صدا در این لحظه ممکن نیست. "
        "پاسخ به صورت متنی ارسال شد."
    )
    print("🔁 Falling back to text-only notice...")

    # Generate a short spoken message as fallback
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
        try:
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=fallback_text
            )
            tmp_mp3.write(response.content)
            tmp_mp3.flush()
            ogg_path = tmp_mp3.name.replace(".mp3", ".ogg")
            AudioSegment.from_mp3(tmp_mp3.name).export(ogg_path, format="ogg")
            print("✅ Fallback voice generated successfully.")
            return ogg_path
        except Exception as e:
            print(f"⚠️ Fallback TTS also failed: {e}")
            return None
