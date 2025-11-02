"""
utils/extractors/ingest_unified.py
----------------------------------
Unified pre-RAG ingestion pipeline.
- Reads PDFs, DOCX, HTML, TXT, MP3, MP4
- Fetches URLs from urls.txt
- Extracts readable text
- Tags each file with country & category metadata
- Saves .txt + .json in cleaned_text_parsed/
"""

import os, re, json, fitz, requests, tempfile
from bs4 import BeautifulSoup
from docx import Document
# from moviepy.editor import VideoFileClip
from urllib.parse import urlparse
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(__file__))     # /utils
SOURCE_DIR = os.path.join(BASE_DIR, "sources", "raw_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "sources", "cleaned_text_parsed")
URL_LIST = os.path.join(SOURCE_DIR, "urls.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# Utility
# -----------------------------
def save_text(out_path, text):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text.strip())

def detect_country_from_url(url_or_name):
    mapping = {
        "switzerland": "Switzerland",
        "netherlands": "Netherlands",
        "germany": "Germany",
        "italy": "Italy",
        "canada": "Canada",
        "usa": "USA",
        "uk": "United Kingdom",
        "sweden": "Sweden"
    }
    lower = url_or_name.lower()
    for k, v in mapping.items():
        if k in lower:
            return v
    return "General"

def detect_category_from_text(text, url=""):
    categories = ["visa", "scholarship", "funding", "tuition", "work", "residence", "study", "admission"]
    combined = f"{url} {text[:1000].lower()}"  # only first part to speed up
    for c in categories:
        if c in combined:
            return c
    return "general"

# -----------------------------
# Extractors
# -----------------------------
def extract_pdf(path):
    text = ""
    try:
        doc = fitz.open(path)
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
    except Exception as e:
        print(f"⚠️ PDF error {path}: {e}")
    return text

def extract_docx(path):
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"⚠️ DOCX error {path}: {e}")
        return ""

def extract_html(path):
    try:
        html = open(path, "r", encoding="utf-8").read()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "img", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text)
    except Exception as e:
        print(f"⚠️ HTML error {path}: {e}")
        return ""

def extract_web(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ApplyPalBot/1.0)"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "img", "nav", "header", "footer"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text)
    except Exception as e:
        print(f"⚠️ Web fetch failed {url}: {e}")
        return ""

def extract_audio(path):
    try:
        with open(path, "rb") as f:
            transcript = client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=f)
            return transcript.text
    except Exception as e:
        print(f"⚠️ Audio error {path}: {e}")
        return ""

    #def extract_video(path):
    #try:
        # clip = VideoFileClip(path)
        # temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        # clip.audio.write_audiofile(temp_audio.name, verbose=False, logger=None)
       #  clip.close()
       #  text = extract_audio(temp_audio.name)
       # os.unlink(temp_audio.name)
        #return text
    #except Exception as e:
        #print(f"⚠️ Video error {path}: {e}")
        #return ""

# -----------------------------
# Main ingestion logic
# -----------------------------
def process_file(src_path, rel_path):
    ext = src_path.lower().split(".")[-1]
    out_path = os.path.join(OUTPUT_DIR, os.path.splitext(rel_path)[0] + ".txt")
    meta_path = out_path.replace(".txt", ".json")

    if ext == "pdf":
        text = extract_pdf(src_path)
    elif ext == "docx":
        text = extract_docx(src_path)
    elif ext in ("html", "htm"):
        text = extract_html(src_path)
    elif ext == "txt":
        text = open(src_path, "r", encoding="utf-8").read()
    elif ext in ("mp3", "wav"):
        text = extract_audio(src_path)
    elif ext in ("mp4", "mov", "mkv"):
        print(f"⚠️ Skipping video file: {src_path}")
        text = ""  # prevent UnboundLocalError
    else:
        print(f"⚠️ Unsupported file type: {ext}")
        return

    if not text.strip():
        return

    save_text(out_path, text)
    meta = {
        "source_path": src_path,
        "country": detect_country_from_url(src_path),
        "category": detect_category_from_text(text),
        "type": ext
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved → {out_path}")


def process_urls():
    if not os.path.exists(URL_LIST):
        return
    with open(URL_LIST, "r", encoding="utf-8") as f:
        urls = [u.strip() for u in f if u.strip()]
    for url in urls:
        print(f"\n🌍 Fetching {url}")
        text = extract_web(url)
        if not text:
            continue
        domain = urlparse(url).netloc.replace(".", "_")
        filename = re.sub(r"\W+", "_", urlparse(url).path or "index")
        out_dir = os.path.join(OUTPUT_DIR, "webpages")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{domain}_{filename}.txt")
        save_text(out_path, f"# Source: {url}\n\n{text}")
        meta = {
            "source_url": url,
            "country": detect_country_from_url(url),
            "category": detect_category_from_text(text, url),
            "type": "web"
        }
        with open(out_path.replace(".txt", ".json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"✅ Web text saved → {out_path}")

# -----------------------------
# Ingest all
# -----------------------------
def ingest_all():
    total, converted = 0, 0
    print(f"📂 Scanning source folder: {SOURCE_DIR}")

    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            if file == "urls.txt":
                continue
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, SOURCE_DIR)
            total += 1
            process_file(src_path, rel_path)
            converted += 1

    process_urls()
    print(f"\n🎯 Ingestion complete: {converted}/{total} files processed.")
    print(f"📝 Cleaned text + metadata in: {OUTPUT_DIR}")

# -----------------------------
if __name__ == "__main__":
    ingest_all()
