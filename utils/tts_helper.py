import os
import tempfile
import shutil
from openai import OpenAI
from pydub import AudioSegment
import traceback, subprocess

print("🔊 utils/tts_helper loaded")

ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
AudioSegment.converter = ffmpeg_path
print(f"🎬 Using FFmpeg at: {ffmpeg_path}")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def speak_reply(text: str) -> str:
    """Generate OpenAI TTS (OGG) using streaming API and return file path."""
    try:
        print("🎤 [TTS] called with text length:", len(text))
        if not text.strip():
            print("⚠️ [TTS] Empty text, aborting.")
            return None

        # 1️⃣ Generate MP3 via streaming
        tmp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_mp3.close()
        tmp_mp3_path = tmp_mp3.name
        print(f"🧩 [TTS] Temp MP3 path: {tmp_mp3_path}")

        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text[:1000],
        ) as response:
            response.stream_to_file(tmp_mp3_path)
        print("✅ [TTS] Stream complete, MP3 exists?", os.path.exists(tmp_mp3_path))

        # check file size
        if not os.path.exists(tmp_mp3_path) or os.path.getsize(tmp_mp3_path) < 2000:
            print("⚠️ [TTS] MP3 missing or too small.")
            return None

        # 2️⃣ Convert to OGG
        ogg_path = tmp_mp3_path.replace(".mp3", ".ogg")
        print(f"🧩 [TTS] Converting MP3 → OGG at {ogg_path}")
        AudioSegment.from_mp3(tmp_mp3_path).export(ogg_path, format="ogg")

        if os.path.exists(ogg_path):
            size_kb = os.path.getsize(ogg_path) / 1024
            print(f"✅ [TTS] OGG generated ({size_kb:.1f} KB)")
            return ogg_path
        else:
            print("❌ [TTS] OGG not created.")
            return None

    except Exception as e:
        print(f"💥 [TTS] Exception: {e}")
        traceback.print_exc()
        # optional: verify ffmpeg presence
        try:
            print("🔍 FFmpeg version:\n", subprocess.getoutput("ffmpeg -version"))
        except Exception:
            pass
        return None
