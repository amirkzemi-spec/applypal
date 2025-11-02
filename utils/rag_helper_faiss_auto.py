"""
utils/rag_helper_faiss_auto.py
------------------------------
RAG engine with FAISS + metadata support.
Now reads .txt + .json pairs (country, category, source, type)
from /sources/cleaned_text_parsed/.
"""

import os, json, hashlib, numpy as np, faiss
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = os.path.dirname(__file__)
TEXT_DIR = os.path.join(BASE_DIR, "sources", "cleaned_text_parsed")
INDEX_PATH = os.path.join(BASE_DIR, "vector_index.faiss")
META_PATH = os.path.join(BASE_DIR, "vector_meta.json")

# -----------------------------
# Embedding helpers
# -----------------------------
def get_embedding(text: str):
    """Generate an embedding for text."""
    res = client.embeddings.create(model="text-embedding-3-small", input=text)
    return np.array(res.data[0].embedding, dtype=np.float32)

def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b)+1e-9)

# -----------------------------
# Collect text + metadata
# -----------------------------
def collect_files():
    files = []
    for root, _, fns in os.walk(TEXT_DIR):
        for f in fns:
            if f.endswith(".txt"):
                files.append(os.path.join(root, f))
    return files

def file_hash(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()

def load_text_and_meta(path):
    """Load content and its metadata (if any)."""
    content = open(path, "r", encoding="utf-8").read()
    meta_path = path.replace(".txt", ".json")

    meta = {
        "country": "general",
        "category": "general",
        "source": "",
        "type": "text"
    }

    if os.path.exists(meta_path):
        try:
            meta.update(json.load(open(meta_path, "r", encoding="utf-8")))
        except Exception as e:
            print(f"⚠️ Metadata error for {meta_path}: {e}")

    return content, meta

# -----------------------------
# RAG Engine
# -----------------------------
class RAGEngine:
    def __init__(self):
        self.index = None
        self.meta = []
        self.dim = 1536  # text-embedding-3-small
        self.load_index()

    def load_index(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            self.index = faiss.read_index(INDEX_PATH)
            self.meta = json.load(open(META_PATH, "r", encoding="utf-8"))
            print(f"💾 Loaded FAISS index with {len(self.meta)} entries.")
        else:
            self.index = faiss.IndexFlatIP(self.dim)
            print("⚠️ No FAISS index found. Creating new one...")

    def save_index(self):
        faiss.write_index(self.index, INDEX_PATH)
        json.dump(self.meta, open(META_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"💾 Index + metadata saved ({len(self.meta)} entries).")

    def update_index(self):
        files = collect_files()
        if not files:
            print("⚠️ No text files found.")
            return

        new_embeddings, new_meta = [], []
        added, skipped, modified = 0, 0, 0

        existing_hashes = {m["hash"]: i for i, m in enumerate(self.meta)}

        for f in files:
            h = file_hash(f)
            if h in existing_hashes:
                skipped += 1
                continue

            text, meta = load_text_and_meta(f)
            if not text.strip():
                continue

            emb = get_embedding(text)
            new_embeddings.append(emb)
            doc_meta = {
                "id": f,
                "hash": h,
                "country": meta.get("country", "general"),
                "category": meta.get("category", "general"),
                "source": meta.get("source_url", meta.get("source_path", "")),
                "type": meta.get("type", "text"),
                "content": text[:1000]  # preview
            }
            new_meta.append(doc_meta)
            added += 1

        if new_embeddings:
            embs = np.vstack(new_embeddings)
            self.index.add(embs)
            self.meta.extend(new_meta)

        print(f"\n🧠 RAG update summary:\n"
              f"   ├── {added} new chunks added\n"
              f"   ├── {modified} modified\n"
              f"   └── {skipped} skipped (already in index)")

        self.save_index()
        print(f"✅ Index updated successfully (total: {len(self.meta)} vectors)")

    # -----------------------------
    # Retrieval
    # -----------------------------
    def search(self, query, top_k=3, country=None, category=None):
        if not self.meta:
            return "(knowledge base empty)"

        q_emb = get_embedding(query).reshape(1, -1)
        scores, idxs = self.index.search(q_emb, top_k * 5)
        results = []

        for i, score in zip(idxs[0], scores[0]):
            if i < 0 or i >= len(self.meta):
                continue
            doc = self.meta[i]
            if country and doc.get("country", "").lower() != country.lower():
                continue
            if category and doc.get("category", "").lower() != category.lower():
                continue
            results.append((score, doc))
            if len(results) >= top_k:
                break

        if not results:
            return "(no relevant matches)"

        return "\n\n".join([f"{r[1]['content']}" for r in results])


# -----------------------------
# Run manually
# -----------------------------
if __name__ == "__main__":
    rag = RAGEngine()
    rag.update_index()
    q = "PhD scholarships in the Netherlands"
    print(f"\n💡 {rag.search(q, top_k=3, country='Netherlands', category='scholarship')}")
