<p align="center">
  <img src="https://img.shields.io/badge/Status-Production_Ready-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Cost-$0/month-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Privacy-100%25_Local-blue?style=for-the-badge&logo=lock" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" />
</p>

# 🔍 Local AI Job Finder & Assistant

> **A fully autonomous, GPU-accelerated AI system that scrapes job portals, scores matches against your resume using a local LLM, and sends ranked results to your phone — all running on your own machine. Zero cloud costs. 100% privacy.**

---

## ✨ What It Does

| Feature | Description |
|:---|:---|
| **🔍 Multi-Portal Job Scraping** | Searches LinkedIn, Indeed, Glassdoor, Naukri, Internshala, Wellfound & Foundit concurrently |
| **🧠 AI-Powered Match Scoring** | Local LLM (via Ollama) reads each job description and scores it 0–100 against your profile |
| **📱 Telegram Delivery** | Sends only high-quality matches (≥60%) directly to your phone with one-click apply links |
| **💬 Personal Chatbot** | Optional Telegram bot with customizable personality (`SOUL.md`) for on-the-go conversations |
| **💾 Smart Deduplication** | Never see the same job twice — deduplicates by title + company hash |
| **⏱️ Fully Automated** | Runs on system boot via Windows Task Scheduler or cron — zero manual intervention |
| **🔒 100% Private** | All processing happens locally. Your resume and credentials never leave your machine |

---

## 🏗️ How It Works

```
          ┌─────────────────────────────┐
          │   OS Task Scheduler / Boot  │
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   1. SCRAPE JOB PORTALS     │
          │   LinkedIn • Indeed • Naukri │
          │   Glassdoor • Internshala   │
          │   Wellfound • Foundit       │
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   2. DEDUPLICATE            │
          │   ~500 raw → ~200 unique    │
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   3. AI MATCH SCORING       │
          │   Ollama reads each job     │
          │   vs. your profile → 0-100  │
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   4. TELEGRAM PUSH          │
          │   🟢 ≥80% │ 🟡 ≥70%       │
          │   🔵 ≥60% → sent to phone  │
          └─────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** — [Install Ollama](https://ollama.com/download) (or run via Docker)
- **Telegram Account** — Create a bot via [@BotFather](https://t.me/BotFather) and get your Chat ID from [@userinfobot](https://t.me/userinfobot)
- **NVIDIA GPU** *(recommended, not required)* — 6GB+ VRAM for fast inference. CPU-only mode also works.

### Step 1: Clone & Install

```bash
git clone https://github.com/ArPaN-DS/Personal_Assist.git
cd Personal_Assist

# Create virtual environment
python -m venv assist_enve

# Activate (Windows)
.\assist_enve\Scripts\activate

# Activate (Linux/macOS)
# source assist_enve/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Your Settings

```bash
# Copy all example templates
cp .env.example .env
cp profiles/my_profile.example.md profiles/my_profile.md
cp resumes/master_resume.example.md resumes/master_resume.md
cp SOUL.example.md SOUL.md
```

> **Windows users:** Use `copy` instead of `cp`.

Now edit each file:

| File | What to configure |
|:---|:---|
| `.env` | Your Telegram bot token, chat ID, Ollama URL, model names, your name |
| `profiles/my_profile.md` | Your target roles, skills, location preferences, things to avoid |
| `resumes/master_resume.md` | Your full resume/CV in markdown format |
| `SOUL.md` | *(Optional)* Customize the chatbot's personality and tone |

### Step 3: Setup Ollama

```bash
# Pull the models (choose based on your VRAM)
ollama pull qwen3:4b        # Recommended for job scoring (~3.5GB VRAM)
ollama pull qwen3:1.7b      # Recommended for fast chat (~2.4GB VRAM)

# (Optional) Create optimized chat model with reduced context
ollama create qwen3:fast -f - <<EOF
FROM qwen3:1.7b
PARAMETER num_ctx 8192
EOF
```

### Step 4: Run

```bash
# Run the job scanner (scrapes → scores → sends to Telegram)
python job_finder.py

# OR run the conversational Telegram bot
python bot.py

# OR use the batch scripts (Windows)
# Double-click START_AI.bat to launch everything
# Double-click STOP_AI.bat to free GPU/RAM
```

---

## 📁 Project Structure

```
Personal_Assist/
├── bot.py                           # Telegram chatbot → routes messages to Ollama
├── job_finder.py                    # Multi-portal scraper + AI scorer + Telegram sender
├── requirements.txt                 # Python dependencies
├── .env.example                     # ← Copy to .env and add your credentials
├── .gitignore                       # Protects credentials & personal data
├── START_AI.bat                     # One-click: start Docker + job finder (Windows)
├── STOP_AI.bat                      # One-click: stop all services (Windows)
├── SOUL.example.md                  # ← Copy to SOUL.md and customize bot personality
├── profiles/
│   └── my_profile.example.md        # ← Copy to my_profile.md with your details
├── resumes/
│   └── master_resume.example.md     # ← Copy to master_resume.md with your resume
├── ARCHITECTURE.md                  # Technical architecture deep-dive
├── DATA_FLOW.md                     # Data flow diagrams (Mermaid)
├── CONTRIBUTING.md                  # Contribution guidelines
└── LICENSE                          # MIT License
```

> **Note:** Files marked with `←` are templates. The real files (`.env`, `my_profile.md`, `master_resume.md`, `SOUL.md`) are gitignored and stay local.

---

## 🔧 Configuration Reference

### Environment Variables (`.env`)

| Variable | Required | Description |
|:---|:---:|:---|
| `USER_NAME` | ✅ | Your name (used in bot system prompt) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ✅ | Your personal chat ID from [@userinfobot](https://t.me/userinfobot) |
| `OLLAMA_URL` | ❌ | Ollama API endpoint (default: `http://localhost:11434/api/chat`) |
| `OLLAMA_MODEL` | ❌ | Model for job scoring (default: `qwen3:4b`) |
| `OLLAMA_BOT_MODEL` | ❌ | Model for chatbot (default: `qwen3:fast`) |
| `MATCH_THRESHOLD` | ❌ | Minimum match % to notify (default: `60`) |

### Search Queries

The job finder searches for these roles by default (edit `SEARCH_QUERIES` in `job_finder.py` to customize):

```
NLP Engineer, ML Engineer, AI Engineer, Machine Learning Engineer,
Generative AI Engineer, GenAI Engineer, NLP Researcher,
Deep Learning Engineer, Speech AI Engineer, AI Research Engineer,
LLM Engineer, Data Scientist NLP
```

---

## 🛡️ Security & Privacy

- **All credentials** in `.env` → gitignored, never pushed
- **Your profile & resume** → gitignored, never pushed
- **100% local processing** → no data sent to cloud APIs
- **Telegram token** → rotate periodically via [@BotFather](https://t.me/BotFather)
- **Git history** → cleaned of any sensitive data

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ideas for contributions:**
- Add new job portal scrapers (e.g., RemoteOK, HackerNews Jobs)
- Add support for email delivery alongside Telegram
- Improve the AI scoring prompt for better accuracy
- Add a web dashboard for viewing results
- Add Linux systemd service support

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — free to use, modify, and distribute.

---

<p align="center">
  ⭐ <b>If this project helps your job search, please star the repo!</b> ⭐<br>
  <sub>Built with local AI, zero cloud costs, and a lot of determination.</sub>
</p>
