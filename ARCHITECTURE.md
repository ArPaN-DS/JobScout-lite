<p align="center">
  <img src="https://img.shields.io/badge/JobScout--Lite-Technical_Architecture-6366F1?style=for-the-badge&logo=cpu" height="60" />
</p>

This project is an entirely localized, GPU-accelerated autonomous personal assistant and job search agent. The architecture is designed to bypass traditional cloud API dependencies (like OpenAI GPT or Anthropic Claude) and leverage local consumer GPU/CPU hardware to perform production-grade orchestration and reasoning.

---

## <img src="https://img.shields.io/badge/1._Core_Principles-3B82F6?style=flat-square&logo=shield" height="24" />

1. **Local-First Inferencing**: All LLM processing runs entirely on the host machine using Ollama. No data is sent over the internet to third-party providers, eliminating subscription costs and protecting your privacy.
2. **Specialized Compute Delegation**: Different tasks are assigned to specifically tuned models. Lightweight, low-latency tasks can use a faster model (e.g. 1.7B-3B parameters), while complex structural reasoning and matching logic can use a larger model (e.g. 4B-8B parameters).
3. **Scheduled Lifecycle**: The system wakes up autonomously (via OS Task Scheduler), executes a high-compute workload (scraping + reasoning), delivers matched results to your phone, and exits.

---

## <img src="https://img.shields.io/badge/2._Infrastructure_Layer-10B981?style=flat-square&logo=server" height="24" />

### Hardware Base
- **Host**: Windows 11 / Linux
- **VRAM Constraint Engine**: The fundamental design constraint is fitting LLMs within your GPU's VRAM. If memory spills over to system RAM, the LLM inferences slow down. Therefore, context windows are optimized.
- **CPU Fallback**: Can run on CPU (using Ollama's CPU inference), although GPU execution is highly recommended for speed.

### Service Setup
- **Ollama Server**: Main LLM host running on the GPU/CPU. Bound to `localhost:11434`.

---

## <img src="https://img.shields.io/badge/3._The_Brain_Layer-F59E0B?style=flat-square&logo=openai" height="24" />

The system does not use a "one size fits all" LLM. Instead, it dynamically switches contexts over a unified REST API based on the incoming task payload:

| Capability | Base Model | VRAM / RAM Target | Context Limit | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Conversational Chat** | `qwen3:fast` (or similar) | ~1.5 - 2.5 GB | 8192 tokens | Lightning-speed Telegram responses. Highly interactive latency. Injects `SOUL.md` for personality. |
| **Logic & Match Classifier** | `qwen3:4b` (or similar) | ~3.0 - 4.5 GB | 4096 tokens | Reading raw scraped Jobs + Resume matching. Classifies matches into 3 tiers (`STRONG_MATCH`, `GOOD_MATCH`, `NO_MATCH`). |

---

## <img src="https://img.shields.io/badge/4._The_Body_Layer-8B5CF6?style=flat-square&logo=python" height="24" />

The Python layer is structured as a modular package under `core/` to handle parallel tasks cleanly and support robust unit testing.

### Component Structure
- **`core/config.py`**: Centralized configuration and path management using `pathlib.Path`. Sets up console/file loggers.
- **`core/scrapers.py`**: Web scraper engine using `python-jobspy` (requests/beautifulsoup) supporting LinkedIn, Indeed, Glassdoor, Naukri, Internshala, Wellfound (best-effort), and Foundit.
- **`core/cache.py`**: Persistent, hash-based deduplication cache (`seen_jobs.json`) to filter out previously seen jobs across runs.
- **`core/scorer.py`**: Two-stage scoring pipeline:
  1. *Stage 1 (Keyword Pre-filter)*: Extracts profile keywords, verifies if job has enough matches, skipping LLM scoring for obvious non-matches.
  2. *Stage 2 (LLM Match Classifier)*: Calls Ollama with structured JSON constraints to classify job matches into tiers.
- **`core/notifier.py`**: Formats messages and handles Telegram API interactions, message chunking, and authorization.

### Execution Wrapper Scripts
- **`job_finder.py`**: The autonomous pipeline orchestrator. Wakes up, runs scrapers, deduplicates, pre-filters, scores remaining candidates, and sends ranked match details to Telegram.
- **`bot.py`**: The conversational agent. Uses memory (maintaining the last 20 messages) and personalizes responses via `SOUL.md`.

---

## <img src="https://img.shields.io/badge/5._Security_&_Isolation-EF4444?style=flat-square&logo=lock" height="24" />

- **Authentication Guard**: `bot.py` verifies incoming user messages against the configured `TELEGRAM_CHAT_ID`, rejecting unauthorized interactions.
- **Token Protection**: Telegram bot tokens and API credentials are kept in a local `.env` file, which is excluded from version control via `.gitignore`.
- **Privacy Enforcement**: The repository `.gitignore` explicitly blacklists `.env`, `profiles/my_profile.md`, `SOUL.md`, and `resumes/master_resume.md`. None of your personal data or PII (Personally Identifiable Information) leaves your local machine.


