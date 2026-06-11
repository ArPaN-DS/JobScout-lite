<p align="center">
  <img src="https://img.shields.io/badge/Status-Production-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Cost-$0/month-success?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Privacy-100%25_Local-blue?style=for-the-badge&logo=lock" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" />
</p>

# Local AI Job Finder & Assistant (LAJA)

> A fully autonomous, local AI assistant and job search agent that runs entirely on your own hardware — zero cloud costs, 100% data privacy, and zero reliance on expensive third-party APIs.

LAJA combines local LLM inference (via **Ollama**), automated multi-portal web scraping, AI-powered resume matching, and **Telegram** delivery into a production-grade workflow. You can schedule it to run daily or trigger it on-demand to scan portals, filter jobs that fit your profile, and receive a ranked summary on your phone.

---

## Key Features

- 🔍 **Multi-Portal Scraping**: Scrapes multiple major platforms (LinkedIn, Indeed, Glassdoor, Naukri, Internshala, and more) concurrently.
- 🧠 **Local AI Scoring**: Uses local models (like `qwen3:4b` or any Ollama-supported model) to read job descriptions and score them against your personal profile using strict guidelines.
- 📱 **Telegram Delivery**: Sends ranked matching jobs (e.g. only those scoring 60%+) directly to your phone with direct links and the AI's reasoning.
- 💬 **Conversational Chatbot**: Built-in optional Telegram chatbot with custom persona (`SOUL.md`) to talk to your local model on the go.
- 💾 **Smart Deduplication**: Hashes jobs by company and title so you never receive the same notification twice.
- ⏱️ **Auto-Start & Scheduling**: Easily integrates with Windows Task Scheduler or cron to run in the background on system boot.
- 🔒 **100% Private**: Your resume, profile, and search history stay completely on your machine.

---

## Technical Pipeline

```
          [OS Task Scheduler / Boot]
                      │
                      ▼
            [1. SCRAPE PORTALS]
      Searches LinkedIn, Indeed, Glassdoor, 
      Naukri, Internshala & Wellfound
                      │
                      ▼
            [2. DEDUPLICATE CACHE]
      Filters out already-seen job hashes
                      │
                      ▼
             [3. AI MATCH SCORING]
     Ollama (qwen3:4b) parses description 
    against local profile & assigns score
                      │
                      ▼
            [4. TELEGRAM PUSH]
    Sends matches (e.g. >= 60%) to Telegram 
       with fit percentage & reason
```

---

## Quick Start (5-Minute Setup)

### Prerequisites
- **Python 3.10+**
- **Ollama** installed locally (or running in Docker)
- **Docker Desktop** (optional, for OpenClaw/Ollama containerization)
- **Telegram Account** and a bot token from [@BotFather](https://t.me/BotFather)

### 1. Clone the Repo
```bash
git clone https://github.com/ArPaN-DS/Personal_Assist.git
cd Personal_Assist
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# Create environment
python -m venv assist_enve

# Activate environment (Windows)
.\assist_enve\Scripts\activate

# Activate environment (Linux/macOS)
source assist_enve/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Set Up Configuration Files
Copy the example files and customize them:

```bash
# Copy environment configuration
copy .env.example .env

# Copy profile and resume templates
copy profiles\my_profile.example.md profiles\my_profile.md
copy resumes\master_resume.example.md resumes\master_resume.md
copy SOUL.example.md SOUL.md
```

### 4. Configure environment variables in `.env`
Open `.env` and fill in:
- `USER_NAME` (your name)
- `TELEGRAM_BOT_TOKEN` (from @BotFather)
- `TELEGRAM_CHAT_ID` (from @userinfobot)
- `OLLAMA_URL` (usually `http://localhost:11434/api/chat`)
- `OLLAMA_MODEL` (e.g., `qwen3:4b`)

### 5. Setup Local LLM
Ensure Ollama is running and pull your preferred models:
```bash
ollama pull qwen3:4b
ollama pull qwen3:1.7b
```

---

## Running the Application

### Running the Job Scanner
This searches job portals, evaluates listings using your profile, and sends matches to Telegram:
```bash
python job_finder.py
```

### Running the Conversational Assistant
This starts a standalone Telegram bot connecting you to your local model:
```bash
python bot.py
```

### Resource Control (Windows)
Double-click `START_AI.bat` to spin up containers and run the job finder, or `STOP_AI.bat` to stop all services and free up GPU/RAM resources.

---

## Customizing Your Profile & Resume

### 1. Personal Profile (`profiles/my_profile.md`)
The AI match-scoring model reads this file at runtime to evaluate job postings. Customize it with your target roles, key technical skills, and keywords to avoid (so the AI filters them out).

### 2. Personality Engine (`SOUL.md`)
If using the gateway, you can completely customize how your bot talks. Define rules, tone, and specific trigger responses to make your assistant unique.

---

## License

This project is licensed under the permissive **MIT License** — feel free to fork, modify, and star! See the [LICENSE](file:///d:/personal_job_assist/LICENSE) file for details.

---

<p align="center">
  🌟 <b>If you find this project useful, please consider giving it a star!</b> 🌟
</p>
