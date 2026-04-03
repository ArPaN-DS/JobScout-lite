#  ARIA: Technical Architecture

ARIA (Arpan's Ridiculously Intelligent Assistant) is an entirely localized, GPU-accelerated autonomous system. The architecture is designed to bypass traditional cloud API dependencies (like ChatGPT or Claude) and leverage idle consumer GPU hardware to perform production-grade orchestration and reasoning.

---

## 1. Core Principles

1. **Local-First Inferencing**: All LLM processing runs entirely on the host machine using Ollama. No tokens are sent over the internet, eliminating subscription costs and avoiding data privacy risks.
2. **Specialized Compute Delegation**: Different tasks are assigned to specifically tuned models. Lightweight, low-latency tasks use a quantized 1.7B model, while complex structural reasoning uses a 4B model.
3. **Event-Driven & Scheduled Lifecycle**: The system wakes up autonomously, executes a high-compute workload (scraping + reasoning), delivers results, and goes back to sleep, managed by the host OS.

---

## 2. Infrastructure Layer

### Hardware Base
- **Host**: Windows 11
- **GPU**: NVIDIA RTX 5050 (8GB VRAM) or equivalent.
- **VRAM Constraints Engine**: The fundamental limiting factor is 8GB of VRAM. If memory spills over to system RAM, the LLM inferences become unusably slow. Therefore, contexts are highly constrained.

### Containerization Strategy
Docker serves as the isolated environment for the system's "Brain" components, allowing seamless network routing internally.

1. **Ollama Server Container (`ollama/ollama`)**
   - Main LLM host running natively on the GPU.
   - Bound to `localhost:11434`.
   - Modelfiles are custom-engineered to explicitly limit the context windows (`num_ctx`) to prevent GPU OOM (Out Of Memory) errors.

2. **OpenClaw Gateway Container (`ghcr.io/openclaw/openclaw`)**
   - Serves as the agentic memory layer and personality engine.
   - Responsible for bridging Telegram updates to the underlying Ollama context.
   - Injects `SOUL.md` into the prompt chain to ensure ARIA maintains its distinct personality.

---

## 3. The "Brain" Layer: Dynamic Model Switching

ARIA does not use a "one size fits all" LLM. Instead, it dynamically switches contexts over a unified REST API based on the incoming task payload.

| Capability | Base Model | Parameter Size | Memory Footprint | Context Limit | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Conversational Chat** | `qwen3:fast` | 1.7 Billion | 2.4 GB VRAM | 8192 tokens | Lightning-speed Telegram responses. Highly interactive latency (3-8 seconds). |
| **Logic & Scoring** | `qwen3:4b` | 4.0 Billion | 3.5 GB VRAM | 4096 tokens | Reading raw scraped Jobs + Resume matching. Slower, but higher accuracy logic. |

*Note: The `qwen3:8b` model was originally tested but resulted in 11GB VRAM usage, causing a 35% memory spillover into CPU/System RAM, drastically dropping Tokens-Per-Second (TPS). Moving to dual dynamic models resolved this bottleneck perfectly.*

---

## 4. The "Body" Layer: Script Capabilities

The python layer operates using multiple parallel asynchronous/synchronous processes to connect the outside world to the LLM Brain.

### `job_finder.py` (The Autonomous Recruiter)
- **Scraper Service**: Uses `python-jobspy` (requests + beautifulsoup backends) to ping 8 major portals simultaneously without triggering IP bans. Web endpoints include LinkedIn, Indeed, Glassdoor, and Internshala.
- **Cache Engine**: Implements a localized memory structure to store `title + company` hashes, ensuring Arpan is never pinged about the same job post twice.
- **Scoring Pipeline**: Converts raw HTML descriptions to markdown, bundles it with `my_profile.md`, and queries `qwen3:4b` using strict system prompts to fetch a JSON structured `{ "score": 85, "reason": "..." }` response.

### `bot.py` (The Communication Hub)
- Built on `python-telegram-bot` (`asyncio`).
- Creates a persistent HTTPx session to the Telegram webhook.
- Routes all incoming text straight into OpenClaw/Ollama and streams chunks back into the Telegram UI.

---

## 5. Security & Isolation

- **Zero Exposure**: The Ollama container is mapped to Localhost only.
- **Token Protection**: Webhook auth tokens are managed via `python-dotenv`.
- The repository `.gitignore` explicitly blacklists `.env`, `./profiles`, and `./resumes`. None of Arpan's PII (Personal Identifiable Information) leaves the host machine through version control.
