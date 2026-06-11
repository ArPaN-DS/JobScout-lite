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


def compress_description(description: str, profile_keywords: set[str], max_chars: int = 1000) -> str:
    """
    Intelligently compresses a job description to keep context high-value.
    - Strips common boilerplate footers (About the company, Equal Opportunity, benefits lists).
    - Prioritizes sentences containing key profile keywords.
    - Preserves layout/headers where possible, keeping within max_chars.
    """
    if not description:
        return ""

    # Standardize whitespace and remove excessive newlines
    lines = [line.strip() for line in description.split("\n") if line.strip()]

    # Exclude common boilerplate sections
    boilerplate_indicators = [
        "equal opportunity employer",
        "diversity and inclusion",
        "we are an equal opportunity",
        "benefits include",
        "about the company",
        "about us",
        "how to apply",
        "contact info",
        "employment type",
        "seniority level",
    ]

    pruned_lines = []
    for line in lines:
        line_lower = line.lower()
        if any(indicator in line_lower for indicator in boilerplate_indicators):
            continue
        pruned_lines.append(line)

    cleaned_text = "\n".join(pruned_lines)
    if len(cleaned_text) <= max_chars:
        return cleaned_text

    # If still too long, score sentences based on keyword matches
    sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)

    # Track sentence relevance
    scored_sentences = []
    for sentence in sentences:
        score = sum(1 for kw in profile_keywords if kw.lower() in sentence.lower())
        scored_sentences.append((score, sentence))

    selected_sentences = []
    current_len = 0

    # Always include the first 3 sentences as they contain the role summary
    for i in range(min(3, len(sentences))):
        selected_sentences.append((i, sentences[i]))
        current_len += len(sentences[i]) + 1

    added_indices = set(range(min(3, len(sentences))))

    # Sort remaining by score descending
    remaining_scored = sorted(
        [(score, idx, sent) for idx, (score, sent) in enumerate(scored_sentences) if idx not in added_indices],
        key=lambda x: x[0],
        reverse=True
    )

    for score, idx, sent in remaining_scored:
        if current_len + len(sent) + 1 > max_chars:
            break
        if score > 0 or len(selected_sentences) < 8:
            selected_sentences.append((idx, sent))
            current_len += len(sent) + 1
            added_indices.add(idx)

    # Sort by original index to keep flow
    selected_sentences.sort(key=lambda x: x[0])

    compressed = " ".join([sent for _, sent in selected_sentences])
    return compressed[:max_chars]


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
    max_retries: int = 2,
    feedback_exemplars: Optional[list[dict]] = None
) -> dict:
    """
    Score a single job against the candidate profile using Ollama.
    Returns dict: {"match": "STRONG_MATCH|GOOD_MATCH|NO_MATCH", "reason": str}
    """
    # Truncate profile to essential info (save context window)
    profile_truncated = profile_text[:800]
    profile_keywords = extract_profile_keywords(profile_text)
    description = compress_description(job.get("description", ""), profile_keywords, max_chars=1000)

    # Format dynamic few-shot feedback exemplars and user constraints
    feedback_str = ""
    exclusion_rules = []
    if feedback_exemplars:
        for idx, ex in enumerate(feedback_exemplars[:5], 1):  # Limit to 5 entries to conserve VRAM
            map_val = "STRONG_MATCH" if ex.get("feedback") == "like" else "NO_MATCH"
            ex_reason = ex.get("feedback_reason", "")
            if ex_reason:
                reason = f"User explicitly flagged: '{ex_reason}'"
                if map_val == "NO_MATCH":
                    exclusion_rules.append(f"Strictly classify roles matching '{ex_reason}' as NO_MATCH.")
            else:
                reason = "User liked this job type" if map_val == "STRONG_MATCH" else "User disliked/flagged this job type"

            feedback_str += (
                f"\nExample (User Feedback {idx}):\n"
                f"Job: \"{ex['title']} at {ex.get('company', 'Unknown')} — {ex.get('description', '')[:200]}\"\n"
                f"Output: {{\"match\": \"{map_val}\", \"reason\": \"{reason}\"}}\n"
            )

    system_prompt = SCORING_SYSTEM_PROMPT
    if exclusion_rules:
        system_prompt += "\n\nAdditional User Constraints:\n" + "\n".join(f"- {rule}" for rule in exclusion_rules[:5])

    user_prompt = f"""{FEW_SHOT_EXAMPLES}
{feedback_str}
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
                    {"role": "system", "content": system_prompt},
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


# ─── Cover Letter / Application Pitch Generator ───

PITCH_SYSTEM_PROMPT = """You are a professional career agent. You write a concise, highly persuasive cover letter / application pitch (under 150 words) matching the candidate's resume to a specific job description.

Rules:
- Write in first person ("I").
- Address the hiring team professionally.
- Highlight 2-3 specific skills/projects from the resume that directly match the job requirements.
- Keep the tone confident, clean, and professional.
- Do NOT include any placeholders like [Date], [Company Name], or [Your Name] — write a complete, ready-to-send copy.
- Output ONLY the pitch. No preamble, no postscript, no thinking tokens."""


async def generate_personalized_pitch(
    job: dict,
    resume_text: str,
    client: httpx.AsyncClient,
    max_retries: int = 2
) -> str:
    """
    Generate a tailored application pitch/cover letter matching the resume to the job.
    """
    # Truncate inputs to prevent model context spillover
    resume_truncated = resume_text[:1200]
    description = job.get("description", "")[:800]

    user_prompt = f"""Candidate Resume:
{resume_truncated}

Job Title: {job['title']}
Company: {job.get('company', 'Unknown')}
Location: {job.get('location', 'Unknown')}
Description: {description}

Write a tailored cover letter / application pitch matching my resume to this job:"""

    for attempt in range(max_retries + 1):
        try:
            response = await client.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": PITCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "keep_alive": "30s",
                "options": {
                    "temperature": 0.3,
                    "num_ctx": 4096,
                    "num_thread": 4,
                }
            }, timeout=120.0)

            if response.status_code != 200:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return "Could not generate tailored pitch (Ollama status error)."

            content = response.json().get("message", {}).get("content", "")
            
            # Clean qwen3 thinking tokens if present
            if "<think>" in content:
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            return content.strip()

        except Exception as e:
            logger.warning(f"Error generating pitch for '{job['title']}': {e}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            return f"Could not generate tailored pitch: {str(e)[:50]}"

    return "Could not generate tailored pitch."
