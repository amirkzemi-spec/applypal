# 🇳🇱 ApplyPal (Nika Visa AI Assistant)

**ApplyPal** — also known as **Nika Visa AI** — is an AI-powered Telegram assistant that helps students find scholarships, university programs, and visa guidance worldwide.

---

## ✨ Features

- 🎓 **Personalized Study & Visa Advice** – via GPT-4o Mini + FAISS-based RAG  
- 🗣️ **Voice Input / Output** – converts between voice and text seamlessly  
- ⚖️ **Smart Filtering** – limits options by budget, IELTS, and age for realistic consultation  
- 💬 **Persian + English Support** – answers naturally in the user’s chosen language  
- 🧾 **Subscription Plans** – Free / Starter / Pro tiers with daily and monthly limits  
- 📊 **User Logging** – local SQLite logs for analytics and future fine-tuning  

---

## 🧩 Tech Stack
| Layer | Tools |
|-------|-------|
| Bot Framework | `python-telegram-bot v20` |
| AI Engine | `OpenAI GPT-4o mini` |
| Knowledge Retrieval | `FAISS + OpenAI Embeddings` |
| Voice | `pydub + moviepy + OpenAI TTS` |
| Data Parsing | `BeautifulSoup + PyMuPDF + python-docx` |
| Storage | SQLite (local) or PostgreSQL (Railway) |

---

## 🧰 Installation

```bash
git clone https://github.com/amirkzemi-spec/applypal.git
cd applypal
pip install -r requirements.txt
