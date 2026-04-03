# Technical Architecture

## Overview
ARIA leverages a **Local GPU Pipeline** to achieve zero-cost, private AI processing. The architecture relies heavily on local model hosting via Ollama, communicating seamlessly with Python-based workflow scripts.

## Core Components

1. **Hardware Layer**
   - **GPU**: NVIDIA RTX 5050 (or similar). This is heavily utilized for inferencing AI model layers quickly.
   - **Memory Control**: Context windows are tuned specifically (e.g., `num_ctx: 8192`) to prevent the models from spilling over from dedicated VRAM (Graphics memory) into slower system RAM.

2. **The "Brain" (Ollama Container)**
   - Acts as the main LLM (Large Language Model) server.
   - **`qwen3:fast` (1.7b optimized)**: A quantized smaller model used for real-time Telegram chatting. Fast response time, low VRAM usage (~2.4GB).
   - **`qwen3:4b`**: A smarter, slightly heavier model invoked specifically by `job_finder.py` to accurately score complex resumes and job descriptions.

3. **The "Body" & Integrations**
   - **Telegram API (via httpx & python-telegram-bot)**: Acts as the primary UI/UX for the user. Handles asynchronous message queuing.
   - **Python JobSpy**: A scraping library utilizing BeautifulSoup and direct HTTP calls to retrieve job listings dynamically while avoiding extreme captchas. 
   - **OpenClaw (Optional Gateway)**: Set up via Docker as a persistent context integration bridging system prompts to local components.

4. **Task Scheduler Hook**
   - Windows Task Scheduler binds to `job_finder.py` on login. 

## Processing Pipeline
- User sends a request via Telegram.
- The Python script (`bot.py`) translates the REST message and issues a `POST` request to `http://localhost:11434/api/chat`.
- Ollama processes the context limit, queries the `.gguf` weights natively on the RTX Series GPU.
- Streaming or chunked text is formatted and shuttled back to the Telegram webhook over HTTPx.
