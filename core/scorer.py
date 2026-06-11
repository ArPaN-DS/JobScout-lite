"""
SLM-optimized job scoring pipeline.
Stage 1: Keyword pre-filter (no GPU, instant)
Stage 2: LLM 3-tier classification (Ollama with structured output)
"""

import re
import json
import asyncio
import httpx
from typing import Optional
from core.config import OLLAMA_URL, OLLAMA_MODEL, load_profile, setup_logging

logger = setup_logging("scorer")

# ─── Keyword Pre-filter ──────────────────────────

def extract_profile_keywords(profile_text: str) -> set[str]:
    """Extract skill/role keywords from the candidate profile for pre-filtering."""
    # Common technical keywords to look for
    # This is intentionally broad — false positives are fine, false negatives are not
    keywords = set()

    # Extract words that look like technical terms (capitalized, acronyms, or known patterns)
    # Split on common delimiters
    for line in profile_text.lower().split("\n"):
        # Skip header lines
        if line.strip().startswith("#"):
            continue
        # Extract comma-separated terms (common in skill lists)
        if "," in line:
            for term in line.split(","):
                term = term.strip().strip("-").strip("*").strip()
                if len(term) > 1 and len(term) < 40:
                    keywords.add(term)
        # Extract individual significant words
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9.+#]{1,25}\b', line)
        for word in words:
            if len(word) > 2:
                keywords.add(word.lower())

    # Remove common stop words that sneak in
    stop_words = {
        "the", "and", "for", "with", "that", "this", "from", "are", "was",
        "have", "has", "been", "will", "can", "not", "but", "all", "any",
        "about", "into", "over", "such", "than", "then", "also", "just",
        "more", "most", "some", "very", "like", "well", "role", "work",
        "open", "years", "year", "experience", "strong", "good", "high",
        "new", "first", "last", "long", "great", "little", "own", "other",
        "old", "right", "big", "different", "small", "large", "next",
        "early", "young", "important", "few", "public", "able", "target",
        "avoid", "prefer", "location", "remote", "india", "bangalore",
        "sectors", "keywords", "strengths", "highlight", "priority",
        "order", "contact", "email", "linkedin", "based", "looking",
    }
    keywords -= stop_words

    return keywords


def keyword_prefilter(job: dict, profile_keywords: set[str], min_matches: int = 2) -> bool:
    """
    Quick keyword check — returns True if the job is worth scoring with the LLM.
    Intentionally has LOW bar (high recall, some false positives are okay).
    """
    job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    matches = 0
    for keyword in profile_keywords:
        if keyword in job_text:
            matches += 1
            if matches >= min_matches:
                return True

    return False


# ─── LLM Scorer ──────────────────────────────────

# System prompt — kept short and precise for SLMs
SCORING_SYSTEM_PROMPT = """You are a job matching classifier. You compare a candidate profile against a job posting and classify the match quality.

Rules:
- Output ONLY a JSON object. No other text.
- Use exactly this format: {"match": "STRONG_MATCH", "reason": "brief reason"}
- "match" must be one of: "STRONG_MATCH", "GOOD_MATCH", "NO_MATCH"
- STRONG_MATCH: Core skills align, role title matches, experience level fits
- GOOD_MATCH: Some skills overlap, related role, worth applying
- NO_MATCH: Wrong domain, wrong seniority, or unrelated skills
- "reason" must be under 15 words"""

# Few-shot examples — critical for SLM reliability
FEW_SHOT_EXAMPLES = """Example 1:
Profile skills: Python, PyTorch, NLP, Transformers
Job: "NLP Engineer at AI startup — build transformer models, Python required"
Output: {"match": "STRONG_MATCH", "reason": "Direct NLP role, requires Python and transformers"}

Example 2:
Profile skills: Python, PyTorch, NLP, Transformers
Job: "Data Analyst — SQL, Excel, Tableau dashboards"
Output: {"match": "NO_MATCH", "reason": "Analytics role, no ML/NLP overlap"}

Example 3:
Profile skills: Python, PyTorch, NLP, Transformers
Job: "ML Engineer — computer vision, TensorFlow preferred"
Output: {"match": "GOOD_MATCH", "reason": "ML role but different specialization"}"""


async def score_job_llm(
    job: dict,
    profile_text: str,
    client: httpx.AsyncClient,
    max_retries: int = 2
) -> dict:
    """
    Score a single job against the candidate profile using Ollama.
    Returns dict: {"match": "STRONG_MATCH|GOOD_MATCH|NO_MATCH", "reason": str}
    """
    # Truncate profile to essential info (save context window)
    profile_truncated = profile_text[:800]
    description = job.get("description", "")[:600]

    user_prompt = f"""{FEW_SHOT_EXAMPLES}

Now classify this:
Profile: {profile_truncated}
Job title: {job['title']}
Company: {job.get('company', 'Unknown')}
Location: {job.get('location', 'Unknown')}
Description: {description}
Output: /no_think"""

    for attempt in range(max_retries + 1):
        try:
            response = await client.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": "json",  # Forces structured JSON output at token level
                "keep_alive": "30s",  # Unloads model from VRAM quickly after batch completes
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 2048,  # Optimized context window saves VRAM
                    "num_thread": 4,
                }
            }, timeout=120.0)

            if response.status_code != 200:
                logger.warning(
                    f"Ollama returned {response.status_code} for '{job['title']}' "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"match": "SKIP", "reason": "Ollama error"}

            content = response.json().get("message", {}).get("content", "")
            logger.debug(f"Raw LLM output for '{job['title']}': {content[:200]}")

            # Parse JSON — with the format: "json" flag, this should be clean
            result = _parse_scoring_response(content)
            if result:
                return result

            # If parsing failed, retry with simpler prompt
            if attempt < max_retries:
                logger.warning(
                    f"JSON parse failed for '{job['title']}' (attempt {attempt + 1}), retrying..."
                )
                await asyncio.sleep(1)
                continue

            logger.warning(f"All parse attempts failed for '{job['title']}'. Raw: {content[:200]}")
            return {"match": "SKIP", "reason": "Parse error"}

        except httpx.TimeoutException:
            logger.warning(f"Timeout scoring '{job['title']}' (attempt {attempt + 1})")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            return {"match": "SKIP", "reason": "Timeout"}

        except Exception as e:
            logger.error(f"Unexpected error scoring '{job['title']}': {e}")
            return {"match": "SKIP", "reason": str(e)[:50]}

    return {"match": "SKIP", "reason": "Max retries exceeded"}


def _parse_scoring_response(content: str) -> Optional[dict]:
    """
    Parse the LLM response into a structured match result.
    Handles various output formats that SLMs may produce.
    """
    # Strip thinking tokens if present (qwen3 models)
    if "<think>" in content:
        # Remove everything between <think> and </think>
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # Try direct JSON parse first (most common with format: "json")
    try:
        data = json.loads(content)
        match_val = str(data.get("match", "")).upper()
        if match_val in ("STRONG_MATCH", "GOOD_MATCH", "NO_MATCH"):
            return {
                "match": match_val,
                "reason": str(data.get("reason", ""))[:100]
            }
        # Some models might output score instead of match — handle gracefully
        if "score" in data:
            score = int(data.get("score", 0))
            match_val = "STRONG_MATCH" if score >= 80 else "GOOD_MATCH" if score >= 60 else "NO_MATCH"
            return {
                "match": match_val,
                "reason": str(data.get("reason", ""))[:100]
            }
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: try to extract JSON from within text
    json_patterns = re.findall(r'\{[^{}]+\}', content)
    for pattern in json_patterns:
        try:
            data = json.loads(pattern)
            match_val = str(data.get("match", "")).upper()
            if match_val in ("STRONG_MATCH", "GOOD_MATCH", "NO_MATCH"):
                return {
                    "match": match_val,
                    "reason": str(data.get("reason", ""))[:100]
                }
        except (json.JSONDecodeError, ValueError):
            continue

    # Last resort: look for the classification keywords in raw text
    content_upper = content.upper()
    if "STRONG_MATCH" in content_upper:
        return {"match": "STRONG_MATCH", "reason": "Extracted from raw text"}
    if "GOOD_MATCH" in content_upper:
        return {"match": "GOOD_MATCH", "reason": "Extracted from raw text"}
    if "NO_MATCH" in content_upper:
        return {"match": "NO_MATCH", "reason": "Extracted from raw text"}

    return None


# ─── Match tier helpers ──────────────────────────

MATCH_TIERS = {
    "STRONG_MATCH": {"emoji": "🟢", "label": "Strong Match", "priority": 1},
    "GOOD_MATCH":   {"emoji": "🟡", "label": "Good Match",   "priority": 2},
    "NO_MATCH":     {"emoji": "🔴", "label": "No Match",     "priority": 3},
    "SKIP":         {"emoji": "⚪", "label": "Skipped",      "priority": 4},
}

def get_match_emoji(match_tier: str) -> str:
    return MATCH_TIERS.get(match_tier, MATCH_TIERS["SKIP"])["emoji"]

def get_match_label(match_tier: str) -> str:
    return MATCH_TIERS.get(match_tier, MATCH_TIERS["SKIP"])["label"]
