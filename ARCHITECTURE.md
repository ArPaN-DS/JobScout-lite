# Local AI Job Finder & Assistant: Technical Architecture

This project is an entirely localized, GPU-accelerated autonomous personal assistant and job search agent. The architecture is designed to bypass traditional cloud API dependencies (like OpenAI GPT or Anthropic Claude) and leverage local consumer GPU/CPU hardware to perform production-grade orchestration and reasoning.

---

## 1. Core Principles

1. **Local-First Inferencing**: All LLM processing runs entirely on the host machine using Ollama. No data is sent over the internet to third-party providers, eliminating subscription costs and protecting your privacy.
2. **Specialized Compute Delegation**: Different tasks are assigned to specifically tuned models. Lightweight, low-latency tasks can use a faster model (e.g. 1.7B-3B parameters), while complex structural reasoning and matching logic can use a larger model (e.g. 4B-8B parameters).
3. **Scheduled Lifecycle**: The system wakes up autonomously (via OS Task Scheduler), executes a high-compute workload (scraping + reasoning), delivers matched results to your phone, and exits.

---

## 2. Infrastructure Layer

### Hardware Base
- **Host**: Windows 11 / Linux
- **VRAM Constraint Engine**: The fundamental design constraint is fitting LLMs within your GPU's VRAM. If memory spills over to system RAM, the LLM inferences slow down. Therefore, context windows are optimized.
- **CPU Fallback**: Can run on CPU (using Ollama's CPU inference), although GPU execution is highly recommended for speed.

### Containerization Strategy
Docker serves as the isolated environment for the system's core components, allowing seamless internal network routing.

1. **Ollama Server Container (`ollama/ollama`)**
   - Main LLM host running on the GPU/CPU.
   - Bound to `localhost:11434`.
   - Modelfiles can be customized to explicitly limit context windows (`num_ctx`) to prevent GPU OOM (Out Of Memory) errors.

2. **OpenClaw Gateway Container (`ghcr.io/openclaw/openclaw`)** (Optional)
   - Serves as the agentic memory layer and personality engine.
   - Responsible for bridging Telegram updates to the underlying Ollama context.
   - Injects `SOUL.md` into the prompt chain to maintain a distinct personality.

---

## 3. The "Brain" Layer: Dynamic Model Switching

The system does not use a "one size fits all" LLM. Instead, it dynamically switches contexts over a unified REST API based on the incoming task payload:

| Capability | Base Model | VRAM / RAM Target | Context Limit | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Conversational Chat** | `qwen3:fast` (or similar) | ~1.5 - 2.5 GB | 8192 tokens | Lightning-speed Telegram responses. Highly interactive latency. |
| **Logic & Scoring** | `qwen3:4b` (or similar) | ~3.0 - 4.5 GB | 4096 tokens | Reading raw scraped Jobs + Resume matching. Slower, but higher accuracy logic. |

---

## 4. The "Body" Layer: Script Capabilities

The Python layer operates using parallel asynchronous/synchronous processes to connect the outside world to the local LLM.

### `job_finder.py` (The Autonomous Recruiter)
- **Scraper Service**: Uses `python-jobspy` (requests + beautifulsoup backends) to search multiple major portals simultaneously. Web endpoints include LinkedIn, Indeed, Glassdoor, and Internshala.
- **Cache Engine**: Implements a localized memory structure to store `title + company` hashes, ensuring you are never pinged about the same job post twice.
- **Scoring Pipeline**: Converts raw HTML descriptions to clean text, bundles it with `my_profile.md` (which you configure locally), and queries the scoring model using strict system prompts to fetch a JSON-structured `{ "score": 85, "reason": "..." }` response.

### `bot.py` (The Communication Hub)
- Built on `python-telegram-bot` (`asyncio`).
- Creates a persistent HTTPx session to the Telegram API.
- Routes incoming text straight into Ollama and streams response chunks back to your Telegram UI.

---

## 5. Security & Isolation

- **Zero Exposure**: The Ollama container is mapped to Localhost only.
- **Token Protection**: Telegram bot tokens and API credentials are kept in a local `.env` file, which is excluded from version control via `.gitignore`.
- **Privacy Enforcement**: The repository `.gitignore` explicitly blacklists `.env`, `profiles/my_profile.md`, and `resumes/master_resume.md`. None of your personal data or PII (Personally Identifiable Information) leaves your local machine.

