<p align="center">
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/GPU-RTX_5050_100%25-76B900?style=for-the-badge&logo=nvidia" />
  <img src="https://img.shields.io/badge/Cost-$0/month-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Privacy-100%25_Local-blue?style=for-the-badge&logo=lock" />
</p>

#  ARIA — Arpan's Ridiculously Intelligent Assistant

> A fully autonomous, GPU-accelerated personal AI system that runs entirely on local hardware — zero cloud costs, zero data leaks, maximum intelligence.

ARIA is not a toy chatbot. It's a **production-grade AI pipeline** combining local LLM inference, multi-portal web scraping, AI-powered job matching, and Telegram-based delivery — all orchestrated through Docker containers and Windows Task Scheduler with zero human intervention after boot.

---

##  What ARIA Does

| Capability | Description | Status |
|:---|:---|:---:|
| **Daily AI Assistant** | Conversational chatbot via Telegram with persistent identity and personality (ARIA persona) | ✅ Live |
| **Automated Job Finder** | Scrapes 8+ job portals → deduplicates → AI-scores against resume → sends ranked results to Telegram | ✅ Live |
| **Resume Tailoring** | Reads master resume + job description → generates tailored resume summary via local LLM | ✅ Live |
| **Auto-Start on Boot** | Everything launches automatically when the laptop opens — no manual commands | ✅ Live |
| **One-Click Resource Control** | `START_AI.bat` / `STOP_AI.bat` to toggle the entire system for heavy developer workloads | ✅ Live |

---

##  System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        WINDOWS HOST                             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Task         │  │ START_AI.bat     │  │ STOP_AI.bat      │  │
│  │ Scheduler    │  │ (one-click start)│  │ (one-click stop) │  │
│  │ (on login)   │  └────────┬─────────┘  └──────────────────┘  │
│  └──────┬───────┘           │                                   │
│         │                   ▼                                   │
│  ┌──────▼───────────────────────────────────────────────────┐   │
│  │                   DOCKER ENGINE                          │   │
│  │                                                          │   │
│  │  ┌─────────────────────┐  ┌───────────────────────────┐  │   │
│  │  │  OLLAMA CONTAINER   │  │  OPENCLAW CONTAINER       │  │   │
│  │  │                     │  │                            │  │   │
│  │  │  qwen3:fast (1.7B)  │  │  Gateway + Telegram Bot   │  │   │
│  │  │  ├─ Chat responses  │  │  ├─ Identity (SOUL.md)    │  │   │
│  │  │  │  (2.4GB VRAM)    │  │  ├─ Memory (per-session)  │  │   │
│  │  │  │                  │  │  ├─ Web Search (DDG)       │  │   │
│  │  │  │  qwen3:4b        │◄─┤  └─ Personality engine    │  │   │
│  │  │  │  ├─ Job scoring  │  │                            │  │   │
│  │  │  │  │  (3.5GB VRAM) │  └───────────────────────────-┘  │   │
│  │  │  │  │               │                                  │   │
│  │  │  └──┘               │         ┌────────────────────┐   │   │
│  │  │  RTX 5050 (8GB)     │         │  job_finder.py     │   │   │
│  │  │  100% GPU           │◄────────┤  (Python script)   │   │   │
│  │  └─────────────────────┘         │  ├─ 8 portal       │   │   │
│  │                                  │  │  scrapers        │   │   │
│  └──────────────────────────────────┤  ├─ Deduplication   │   │   │
│                                     │  ├─ AI scoring      │   │   │
│                                     │  └─ Telegram push   │   │   │
│                                     └────────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  LOCAL FILES (.gitignore protected)                    │   │
│  │  ├─ .env (credentials)                                │   │
│  │  ├─ profiles/my_profile.md (candidate profile)        │   │
│  │  └─ resumes/master_resume.md (full resume source)     │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   TELEGRAM API   │
                    │   (User's Phone) │
                    └──────────────────┘
```

---

##  Key Metrics

| Metric | Value |
|:---|:---|
| Jobs scraped per run | **500+** across 8 portals |
| Unique jobs after dedup | **~200** per scan |
| Portals searched | LinkedIn, Indeed, Glassdoor, Naukri, Internshala, Foundit, Wellfound, Company careers |
| Match threshold | **≥60%** profile fit (AI-scored) |
| Scoring model | `qwen3:4b` — accuracy-optimized |
| Chat model | `qwen3:fast` (1.7B, 8K context) — speed-optimized |
| GPU memory (chat) | **2.4 GB** / 8 GB available |
| GPU memory (scoring) | **3.5 GB** / 8 GB available |
| GPU utilization | **100%** (zero CPU spillover) |
| Response latency (chat) | **3–8 seconds** |
| Full job scan time | **45–60 minutes** (213 jobs scored individually) |
| Cloud API costs | **$0/month** — entirely local |
| Privacy | **100%** — no data leaves the machine |

---

##  The Brain: Model Selection & Optimization

A critical engineering decision was choosing the right model for each task within the constraints of an 8GB VRAM budget:

| Model | Parameters | VRAM | Context | Purpose | Why This One? |
|:---|:---|:---|:---|:---|:---|
| `qwen3:8b` | 8B | 11 GB | 40K | ❌ Rejected | Exceeds VRAM → 35% CPU spillover, unacceptably slow |
| `qwen3:4b` | 4B | 3.5 GB | 4K | ✅ Job scoring | Best accuracy-to-memory ratio for structured JSON output |
| `qwen3:fast` | 1.7B | 2.4 GB | 8K | ✅ Daily chat | Custom Modelfile with `num_ctx 8192`; fast, fits fully in GPU |

### VRAM Optimization Strategy
```
Problem:  qwen3:8b (default) → 11GB VRAM → spills to CPU → 3x slower
Solution: Custom Modelfile with reduced context window

# /tmp/Modelfile
FROM qwen3:1.7b
PARAMETER num_ctx 8192    ← reduced from 40960 (default)

Result: 6.2GB → 2.4GB VRAM (62% reduction), zero quality loss for chat
```

---

##  Job Finder Pipeline — How It Works

```
STEP 1: COLLECTION (parallel scraping)
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  LinkedIn    │ │   Indeed     │ │  Glassdoor   │ │   Naukri     │
│  (JobSpy)    │ │  (JobSpy)   │ │  (JobSpy)    │ │  (BS4)       │
└──────┬───────┘ └──────┬──────┘ └──────┬───────┘ └──────┬──────┘
       │                │               │                │
       └────────────────┴───────────────┴────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  + Internshala (BS4)   │
                    │  + Foundit (BS4)       │
                    │  + Wellfound (regex)   │
                    │  + Company pages       │
                    └───────────┬───────────┘
                                │
                        ~500 raw jobs
                                │
STEP 2: DEDUPLICATION           ▼
                    ┌───────────────────────┐
                    │  Title + Company key   │
                    │  normalization         │
                    │  ~500 → ~213 unique    │
                    └───────────┬───────────┘
                                │
STEP 3: AI SCORING              ▼
                    ┌───────────────────────┐
                    │  For each job:        │
                    │  ┌─────────────────┐  │
                    │  │ Candidate Profile│  │
                    │  │ + Job Description│  │
                    │  │ → qwen3:4b       │  │
                    │  │ → JSON {score,   │  │
                    │  │    reason}        │  │
                    │  └─────────────────┘  │
                    │  Temp: 0.1 (strict)   │
                    │  Threshold: ≥60%      │
                    └───────────┬───────────┘
                                │
STEP 4: DELIVERY                ▼
                    ┌───────────────────────┐
                    │  Sort by score (desc)  │
                    │  Format HTML messages   │
                    │  🟢 ≥80% | 🟡 ≥70%    │
                    │  🔵 ≥60%               │
                    │  Send to Telegram       │
                    │  (max 30 jobs)          │
                    └───────────────────────┘
```

### Search Queries (12 targeted queries)
```
NLP Engineer, ML Engineer, AI Engineer, Machine Learning Engineer, 
Generative AI Engineer, GenAI Engineer, NLP Researcher, 
Deep Learning Engineer, Speech AI Engineer, AI Research Engineer, 
LLM Engineer, Data Scientist NLP
```

### Progress Monitoring
The system sends **Telegram progress updates every 5 minutes** during operation:
- Collection phase: queries completed, jobs found so far
- Scoring phase: jobs scored, matches found, errors encountered
- Completion: total time, final match count, ranked results

---

##  ARIA's Personality Engine

ARIA isn't a generic chatbot — she has a defined personality loaded via `SOUL.md` into OpenClaw's workspace:

| Trait | Behavior |
|:---|:---|
| **Mysterious** | "Ah, Arpan. I had a feeling you'd ask that." |
| **Playful** | "Another resume request? My circuits weep... but let's make it legendary." |
| **Professional** | Switches instantly to sharp, precise mode for technical work |
| **Self-aware** | "Even I have limits. Shocking, I know." |

Identity is persisted through OpenClaw's `USER.md` + `SOUL.md` workspace files, ensuring ARIA always knows who Arpan is and maintains character across sessions.

---

##  Tech Stack

| Layer | Technology |
|:---|:---|
| **LLM Runtime** | Ollama (Docker container) |
| **Models** | Qwen3 1.7B (chat), Qwen3 4B (scoring) |
| **GPU** | NVIDIA RTX 5050 (8GB VRAM, 100% utilization) |
| **Agent Framework** | OpenClaw (Docker container, gateway + memory + web search) |
| **Web Scraping** | python-jobspy, BeautifulSoup4, requests, regex |
| **Messaging** | Telegram Bot API (python-telegram-bot, httpx) |
| **Async Runtime** | Python asyncio + httpx.AsyncClient |
| **Automation** | Windows Task Scheduler (login trigger) |
| **Credential Mgmt** | python-dotenv (.env file, gitignored) |
| **Containerization** | Docker (restart: always, auto-boot) |
| **Search** | DuckDuckGo (OpenClaw plugin, free, no API key) |

---

##  Project Structure

```
Personal_Assist/
├── bot.py                 # Telegram chatbot — routes messages to Ollama
├── job_finder.py          # Multi-portal scraper + AI scorer + Telegram sender
├── START_AI.bat           # One-click: start Docker containers + job finder
├── STOP_AI.bat            # One-click: stop all AI services, free GPU
├── SOUL.md                # ARIA personality definition (loaded into OpenClaw)
├── .env                   # Credentials (TELEGRAM_TOKEN, OLLAMA_URL, etc.)
├── .gitignore             # Excludes .env, profiles/, resumes/, venv
├── ARCHITECTURE.md        # Technical architecture deep-dive
├── DATA_FLOW.md           # Data flow diagrams (Mermaid)
├── profiles/
│   └── my_profile.md      # Candidate profile (target roles, skills, preferences)
└── resumes/
    └── master_resume.md   # Full master resume (all experience, publications)
```

---

##  Quick Start

### Prerequisites
- **NVIDIA GPU** with 8GB+ VRAM
- **Docker Desktop** (with WSL2 backend on Windows)
- **Python 3.10+** with virtual environment
- **Telegram** account + Bot Token from [@BotFather](https://t.me/BotFather)

### 1. Clone & Setup
```bash
git clone https://github.com/ArPaN-DS/Personal_Assist.git
cd Personal_Assist
python -m venv assist_enve
.\assist_enve\Scripts\activate        # Windows
pip install python-jobspy requests beautifulsoup4 httpx python-telegram-bot python-dotenv
```

### 2. Configure `.env`
```ini
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_user_id
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=qwen3:4b
OLLAMA_BOT_MODEL=qwen3:fast
```

### 3. Start Docker Containers
```bash
# Ollama (LLM server)
docker run -d --gpus all --restart always --name ollama -p 11434:11434 ollama/ollama
docker exec -it ollama ollama pull qwen3:4b
docker exec -it ollama ollama pull qwen3:1.7b

# Create optimized chat model
docker exec -it ollama sh -c 'echo "FROM qwen3:1.7b\nPARAMETER num_ctx 8192" > /tmp/Modelfile && ollama create qwen3:fast -f /tmp/Modelfile'

# OpenClaw (agent gateway + Telegram bridge)
docker run -d --restart always --name openclaw -v C:\openclaw:/home/node/.openclaw -p 18789:18789 ghcr.io/openclaw/openclaw:latest
```

### 4. Run
```bash
# Option A: Double-click START_AI.bat (recommended)
# Option B: Manual
python job_finder.py      # Run job scan
python bot.py             # Run standalone chatbot (without OpenClaw)
```

---

##  Security

- **All credentials** stored in `.env` (gitignored — never pushed to GitHub)
- **Personal data** (`profiles/`, `resumes/`) excluded from version control
- **Telegram token** should be rotated periodically via [@BotFather](https://t.me/BotFather)
- **100% local processing** — no data sent to cloud APIs

---

##  License

This is a personal project built for private use. Not intended for redistribution.

---

<p align="center">
  <b>Built by <a href="https://github.com/ArPaN-DS">Arpan Majumdar</a></b><br>
  <i>ML/NLP Engineer · ACL 2025 · CLEF 2025 · RTX-powered local AI</i>
</p>
