"""
utils/rag_loader.py
-------------------
Recursively scan ./sources/cleaned_text/ for .txt files
and build a structured JSON file at ./sources/structured_json/knowledge.json
for scalable RAG ingestion.
"""

import os
import json
import re
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
TEXT_DIR = os.path.join(BASE_DIR, "sources", "cleaned_text")
OUT_PATH = os.path.join(BASE_DIR, "sources", "structured_json", "knowledge.json")


def detect_category(filename: str) -> str:
    """Infer category from filename keywords."""
    fname = filename.lower()
    if "visa" in fname or "law" in fname or "permit" in fname:
        return "visa"
    elif "scholar" in fname or "fund" in fname:
        return "scholarship"
    elif "university" in fname or "admission" in fname or "program" in fname:
        return "university"
    elif "fee" in fname or "cost" in fname or "tuition" in fname:
        return "finance"
    else:
        return "general"


def chunk_text(text: str, max_length: int = 1500) -> list:
    """Split text into smaller chunks for efficient embeddings."""
    sentences = re.split(r'(?<=[.!؟])\s+', text)
    chunks, buffer = [], ""

    for sent in sentences:
        if len(buffer) + len(sent) < max_length:
            buffer += " " + sent
        else:
            chunks.append(buffer.strip())
            buffer = sent
    if buffer:
        chunks.append(buffer.strip())

    return [chunk for chunk in chunks if chunk]


def build_knowledge_json():
    """Main converter: scan subfolders and build structured JSON."""
    print(f"📂 Scanning {TEXT_DIR} for .txt files...")
    docs = []

    for root, dirs, files in os.walk(TEXT_DIR):
        for file in files:
            if not file.endswith(".txt"):
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content:
                    continue

                # Folder name = country (last folder in path)
                country = os.path.basename(root)
                category = detect_category(file)
                chunks = chunk_text(content)

                for idx, chunk in enumerate(chunks):
                    docs.append({
                        "id": f"{country}_{file}_{idx}",
                        "country": country,
                        "category": category,
                        "source_file": file,
                        "content": chunk,
                        "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    })

                print(f"✅ {country}/{file} → {len(chunks)} chunks ({len(content)} chars)")

            except Exception as e:
                print(f"⚠️ Could not read {path}: {e}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print(f"\n🎯 Done! Saved {len(docs)} entries to {OUT_PATH}")


if __name__ == "__main__":
    build_knowledge_json()
