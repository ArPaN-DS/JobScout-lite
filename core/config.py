"""
Centralized configuration for the Local AI Job Finder.
Loads all settings from .env and profile files once at import time.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_PATH = PROJECT_ROOT / "profiles" / "my_profile.md"
SOUL_PATH = PROJECT_ROOT / "SOUL.md"
CACHE_DIR = PROJECT_ROOT / os.getenv("CACHE_DIR", "jobs_cache")
LOG_DIR = PROJECT_ROOT / "logs"

# ─── Telegram ────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ─── Ollama ──────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_BOT_MODEL = os.getenv("OLLAMA_BOT_MODEL", "qwen3:fast")

# ─── User ────────────────────────────────────────
USER_NAME = os.getenv("USER_NAME", "User")

# ─── Logging ─────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def setup_logging(name: str = "job_finder") -> logging.Logger:
    """Configure and return a logger that writes to both console and file."""
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    from datetime import datetime
    log_file = LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# ─── Profile Loading ────────────────────────────
def load_profile() -> str:
    """Load the candidate profile from profiles/my_profile.md."""
    if PROFILE_PATH.exists():
        return PROFILE_PATH.read_text(encoding="utf-8")
    else:
        default = (
            "Role: AI/ML Engineer\n"
            "Skills: Python, PyTorch, Large Language Models, NLP\n"
            "Location: Remote / Open to relocation\n"
        )
        logging.getLogger("job_finder").warning(
            f"Profile not found at {PROFILE_PATH}. Using default placeholder."
        )
        return default

def load_soul() -> str:
    """Load the SOUL.md personality file for the bot."""
    if SOUL_PATH.exists():
        content = SOUL_PATH.read_text(encoding="utf-8")
        # Replace {USER_NAME} placeholder with actual user name
        return content.replace("{USER_NAME}", USER_NAME)
    return ""

# ─── Search Queries ──────────────────────────────
SEARCH_QUERIES = [
    "NLP Engineer",
    "ML Engineer",
    "AI Engineer",
    "Machine Learning Engineer",
    "Generative AI Engineer",
    "GenAI Engineer",
    "NLP Researcher",
    "Deep Learning Engineer",
    "Speech AI Engineer",
    "AI Research Engineer",
    "LLM Engineer",
    "Data Scientist NLP",
]
