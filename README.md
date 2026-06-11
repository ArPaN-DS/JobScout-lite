<p align="center">
  <img src="https://img.shields.io/badge/Status-Production_Ready-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Cost-$0/month-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Privacy-100%25_Local-blue?style=for-the-badge&logo=lock" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" />
</p>

# 🔍 JobScout-Lite

### **Your Autonomous Local AI Recruiter & Personal Agent**

> **JobScout-Lite is a fully autonomous, GPU-accelerated AI recruiting agent that works for *you*. It scrapes major job portals, filters matches against your profile, scores compatibility using locally-run LLMs via Ollama, and delivers structured, prioritized reports straight to your Telegram. 100% Private. 100% Free. 100% Local.**

<p align="center">
  <a href="#-features-at-a-glance"><img src="https://img.shields.io/badge/Features-Local_AI-blueviolet?style=flat-square" /></a>
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Get_Started-5_Minutes-success?style=flat-square" /></a>
  <a href="https://github.com/ArPaN-DS/JobScout-lite/stargazers"><img src="https://img.shields.io/github/stars/ArPaN-DS/JobScout-lite?style=flat-square&color=gold" /></a>
</p>

---

## 💡 Why JobScout-Lite?

In a crowded job market, finding the right role shouldn't mean spending hours manually parsing listing boards or sending your personal resume to third-party scrapers. 

* 💸 **Zero API Cost**: Powered entirely by state-of-the-art local SLMs/LLMs (like `Qwen2.5` / `Qwen3` / `Llama3`). No OpenAI API tokens or subscriptions required.
* 🔒 **Ultimate Privacy**: Your resume, skills, target compensation, and locations never leave your machine.
* ⚡ **Smart Filtering**: The two-stage pre-filtering engine ensures you don't waste precious GPU cycles or time scanning irrelevant matches.
* 💬 **Double-Agent Utility**: Includes both an automated **Pipeline Orchestrator** (to run on system boot) and an interactive **Conversational Chatbot** (with custom personality via `SOUL.md`).

---

## 🛠️ Features at a Glance

| Engine / Component | Capability | Tech Under the Hood |
| :--- | :--- | :--- |
| **🌐 Aggregator Scraper** | Parallel scraping across LinkedIn, Indeed, Glassdoor, Naukri, Internshala, Wellfound, and Foundit. | `python-jobspy` + `BeautifulSoup` + `asyncio` |
| **⚡ Stage-1 Pre-Filter** | Filters out obvious mismatch roles instantly based on profile keywords before invoking LLM logic. | Python RegEx (Instant, 0 GPU cost) |
| **🧠 Stage-2 LLM Classifier** | Classifies compatibility into `STRONG_MATCH`, `GOOD_MATCH`, or `NO_MATCH` with structured JSON reasons. | `Ollama` + SLM (`qwen3:4b` / `llama3`) |
| **📱 Telegram Delivery** | Instantly dispatches ranked job detail cards, direct apply links, and AI matching explanations. | `python-telegram-bot` + Markdown formatting |
| **💬 Interactive Chatbot** | A conversational companion bot with conversation memory and custom personality injection (`SOUL.md`). | `python-telegram-bot` + `httpx` stream |
| **💾 Smart Cache** | Hash-based deduplication ensuring you never see the same job post twice across separate runs. | JSON local database store |
| **⏱️ Wake & Sleep Scheduler** | Runs silently in the background on startup, processes new postings, and automatically unloads models. | Windows Task Scheduler / Startup batch scripts |

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
          │   Filter against local cache│
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   3. KEYWORD PRE-FILTER     │
          │   Filters out non-matching  │
          │   roles without GPU cost    │
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   4. AI MATCH CLASSIFIER    │
          │   Ollama classifies matches │
          │   as Strong, Good, or None  │
          └─────────────┬───────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   5. TELEGRAM PUSH          │
          │   🟢 Strong Match           │
          │   🟡 Good Match             │
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
git clone https://github.com/ArPaN-DS/JobScout-lite.git
cd JobScout-lite

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

### Step 5: Running Tests

To run the unit and integration tests and verify that the system is fully functional:

```bash
# Activate virtual environment if not already active
# Windows:
.\assist_enve\Scripts\activate
# Linux/macOS:
# source assist_enve/bin/activate

# Run test suite
python -m pytest tests/ -v --tb=short
```

---


## 📁 Project Structure

```
JobScout-Lite/
├── bot.py                           # Conversational Telegram bot (with memory/auth)
├── job_finder.py                    # Autonomous pipeline orchestrator wrapper
├── core/                            # Core functionality package
│   ├── __init__.py                  # Package initialization
│   ├── cache.py                     # Persistent deduplication cache
│   ├── config.py                    # Centralized settings & path configuration
│   ├── notifier.py                  # Telegram message formatting & delivery
│   ├── scrapers.py                  # Portal search scrapers (LinkedIn, Naukri, etc.)
│   └── scorer.py                    # Two-stage job match scoring pipeline
├── tests/                           # Pytest unit & integration test suite
│   ├── __init__.py                  # Test suite setup
│   ├── test_cache.py                # Cache deduplication tests
│   ├── test_config.py               # Config loading tests
│   ├── test_notifier.py             # Telegram notifier & auth tests
│   ├── test_scorer.py               # Matching classification & parsing tests
│   └── fixtures/                    # Mock responses and data fixtures
├── jobs_cache/                      # Persistent cache directory (gitignored)
├── logs/                            # Local application log files (gitignored)
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment settings template
├── .gitignore                       # Protects credentials & cache files
├── START_AI.bat                     # Runs job finder on startup (Windows)
├── STOP_AI.bat                      # Stops background AI services (Windows)
├── SOUL.example.md                  # Template for bot personality
├── profiles/
│   └── my_profile.example.md        # Template for your profile configuration
├── resumes/
│   └── master_resume.example.md     # Template for master resume
├── ARCHITECTURE.md                  # Technical architecture deep-dive
├── DATA_FLOW.md                     # Data flow diagrams
├── CONTRIBUTING.md                  # Contribution guidelines
└── LICENSE                          # MIT License
```

> **Note:** Files marked with templates (`.example`) should be copied to their real names (without `.example`), which are gitignored to prevent pushing sensitive data.

---

## 🔧 Configuration Reference

### Environment Variables (`.env`)

| Variable | Required | Description |
|:---|:---:|:---|
| `USER_NAME` | ✅ | Your name (used in bot system prompt) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ✅ | Your personal chat ID from [@userinfobot](https://t.me/userinfobot) |
| `OLLAMA_URL` | ❌ | Ollama API endpoint (default: `http://localhost:11434/api/chat`) |
| `OLLAMA_MODEL` | ❌ | Model for job classification (default: `qwen3:4b`) |
| `OLLAMA_BOT_MODEL` | ❌ | Model for chatbot (default: `qwen3:fast`) |
| `LOG_LEVEL` | ❌ | Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`) |
| `CACHE_DIR` | ❌ | Deduplication cache folder name (default: `jobs_cache`) |

### Search Queries

The job finder searches for these roles by default (edit `SEARCH_QUERIES` in `core/config.py` to customize):


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
