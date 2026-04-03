# ARIA: Arpan's Ridiculously Intelligent Assistant

Welcome to the **Personal Assist** project! This repository contains the code and configuration for a fully autonomous, local, and incredibly smart AI assistant named **ARIA**. 

ARIA serves three main goals without sending your private data to paid APIs:
1. **Daily Assistant**: A Telegram chatbot running off a local AI model, preserving conversational memory and answering your questions.
2. **Job Finder**: An automated crawler that searches various job boards for roles matching your specific criteria, scores them with AI, and sends direct links to Telegram.
3. **Resume Tailoring**: Reads your profile data and uses state-of-the-art Generative AI to tailor your resume outputs directly.

## How It Works (For Non-Techies)
Think of ARIA as having two main parts:
- **The Brain (Ollama)**: We use a powerful local AI model called `qwen3` running directly on your computer's graphics card. This means it's super fast, 100% private, and completely free.
- **The Body (Telegram Bot & Job Finder)**: This is the code that talks to the Brain. It logs onto Telegram to chat with you and surfs the web quietly in the background to scrape jobs from LinkedIn, Indeed, etc.

## Setup & Configuration 

### 1. Prerequisites
- **Ollama**: Must be installed and running on your machine.
- **Docker**: Used to run `OpenClaw` (an optional gateway if used for broader integrations).
- **Python 3.x**: Installed alongside a virtual environment.

### 2. Environment Variables (`.env`)
To run this project securely, create a file named `.env` in the root folder with the following details:
```ini
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=qwen3:4b
OLLAMA_BOT_MODEL=qwen3:fast
```
*(Do not share your `.env` file!)*

## Scripts Overview

### `bot.py`
This runs the Telegram chatbot! It listens to your messages on Telegram and forwards them to the local `qwen3:fast` model to provide quick conversational responses.

### `job_finder.py`
This is your personal recruiter.
- It wakes up, checks platforms like LinkedIn, Indeed, Glassdoor, and Internshala.
- Collects jobs based on queries like "NLP Engineer" or "GenAI Engineer".
- Eliminates duplicate postings.
- Asks the local AI brain to "score" the job out of 100 based on your profile.
- Finally, it pings your Telegram with the top matching jobs and apply links.

### `START_AI.bat` / `STOP_AI.bat`
Quick double-click files to start or stop the AI models respectively, freeing up your computer's resources when you need them for heavy tasks.

## Security Disclaimer
This project includes personal resumes and AI instruction profiles (kept locally but excluded via `.gitignore`). Please double check your Bot Token periodically to ensure safety.

---
*Built customized for Arpan Majumdar, leveraging local AI hardware capabilities.*
