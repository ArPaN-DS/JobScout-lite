"""
╔══════════════════════════════════════════════════════════════╗
║               LOCAL AI JOB FINDER — job_finder.py            ║
║  Searches all portals → Scores with Ollama → Sends Telegram ║
╚══════════════════════════════════════════════════════════════╝

USAGE:  python job_finder.py
"""

import asyncio
import time
import httpx
import requests as req
from datetime import datetime

from core.config import (
    OLLAMA_URL, OLLAMA_MODEL, SEARCH_QUERIES,
    load_profile, setup_logging
)
from core.scrapers import search_all
from core.scorer import (
    extract_profile_keywords, keyword_prefilter,
    score_job_llm, get_match_emoji, get_match_label
)
from core.cache import JobCache
from core.notifier import send_telegram, format_job_message

logger = setup_logging("job_finder")


async def main():
    start_time = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"  LOCAL AI JOB FINDER — {start_time.strftime('%d %b %Y, %I:%M %p')}")
    logger.info(f"{'='*60}")

    # Load profile and extract keywords for pre-filtering
    profile_text = load_profile()
    profile_keywords = extract_profile_keywords(profile_text)
    logger.info(f"Loaded profile with {len(profile_keywords)} keywords for pre-filtering")

    # Initialize persistent cache
    cache = JobCache()
    cache.cleanup_expired()
    logger.info(f"Cache loaded: {cache.size} previously seen jobs")

    # Send start notification
    await send_telegram(
        f"🔍 <b>Job Finder Started</b>\n"
        f"📅 {start_time.strftime('%d %b %Y, %I:%M %p')}\n"
        f"🎯 Scanning: LinkedIn, Indeed, Naukri, Internshala, Wellfound, Foundit\n"
        f"⏳ Results in ~30-45 min."
    )

    # ── STEP 1: Scrape all portals ──────────────────────
    logger.info("STEP 1: Collecting jobs from all portals...")
    all_jobs = search_all(SEARCH_QUERIES)
    logger.info(f"Total collected: {len(all_jobs)} raw jobs")

    # ── STEP 2: Deduplicate (persistent) ────────────────
    logger.info("STEP 2: Deduplicating against history...")
    novel_jobs = cache.deduplicate(all_jobs)
    logger.info(f"After dedup: {len(novel_jobs)} novel jobs")

    if not novel_jobs:
        await send_telegram(
            "😕 <b>No new jobs found today</b>\n"
            f"Scanned {len(all_jobs)} listings, all previously seen.\n"
            "Try again tomorrow."
        )
        logger.info("No novel jobs. Exiting.")
        return

    # ── STEP 3: Keyword pre-filter ──────────────────────
    logger.info("STEP 3: Keyword pre-filtering...")
    candidates = [j for j in novel_jobs if keyword_prefilter(j, profile_keywords)]
    skipped = len(novel_jobs) - len(candidates)
    logger.info(f"Pre-filter: {len(candidates)} candidates, {skipped} rejected by keywords")

    await send_telegram(
        f"📦 <b>Collection Complete!</b>\n"
        f"New jobs found: <b>{len(novel_jobs)}</b>\n"
        f"After keyword filter: <b>{len(candidates)}</b>\n"
        f"🧠 Now scoring with {OLLAMA_MODEL}..."
    )

    # ── STEP 4: LLM scoring ────────────────────────────
    logger.info(f"STEP 4: Scoring {len(candidates)} jobs with {OLLAMA_MODEL}...")
    strong_matches = []
    good_matches = []
    errors = 0

    async with httpx.AsyncClient() as client:
        for i, job in enumerate(candidates):
            logger.info(f"  [{i+1}/{len(candidates)}] {job['title']} @ {job.get('company', '?')[:30]}")

            result = await score_job_llm(job, profile_text, client)
            job["match_tier"] = result["match"]
            job["match_reason"] = result.get("reason", "")

            if result["match"] == "STRONG_MATCH":
                strong_matches.append(job)
                logger.info(f"    → 🟢 STRONG_MATCH: {result.get('reason', '')}")
            elif result["match"] == "GOOD_MATCH":
                good_matches.append(job)
                logger.info(f"    → 🟡 GOOD_MATCH: {result.get('reason', '')}")
            elif result["match"] == "SKIP":
                errors += 1
                logger.warning(f"    → ⚪ SKIP (error): {result.get('reason', '')}")
            else:
                logger.info(f"    → 🔴 NO_MATCH")

    # ── STEP 5: Send results to Telegram ────────────────
    matched_jobs = strong_matches + good_matches
    elapsed = (datetime.now() - start_time).seconds // 60
    logger.info(f"STEP 5: Sending {len(matched_jobs)} results to Telegram...")

    if not matched_jobs:
        await send_telegram(
            f"😕 <b>No matches found today</b>\n"
            f"Scanned {len(all_jobs)} jobs, scored {len(candidates)}.\n"
            f"None classified as Strong or Good match.\n"
            f"⏱️ Time: {elapsed} min"
        )
        return

    # Header
    await send_telegram(
        f"✅ <b>Job Scan Complete!</b>\n"
        f"📊 Scanned: <b>{len(all_jobs)}</b> total jobs\n"
        f"🟢 Strong matches: <b>{len(strong_matches)}</b>\n"
        f"🟡 Good matches: <b>{len(good_matches)}</b>\n"
        f"⏱️ Time: <b>{elapsed} min</b>\n"
        f"📅 {start_time.strftime('%d %b %Y')}\n\n"
        f"👇 <b>Results ranked by match quality:</b>"
    )

    # Send each matched job (max 30)
    for i, job in enumerate(matched_jobs[:30], 1):
        await send_telegram(format_job_message(job, i))
        await asyncio.sleep(0.3)

    # Footer
    await send_telegram(
        f"🏁 <b>That's all for today!</b>\n"
        f"Errors/skips: {errors}\n"
        f"Next scan: tomorrow at startup."
    )

    logger.info(f"{'='*60}")
    logger.info(f"  Done! Sent {len(matched_jobs[:30])} jobs to Telegram")
    logger.info(f"  Total time: {elapsed} minutes")
    logger.info(f"{'='*60}")


def wait_for_ollama(max_attempts: int = 12, interval: int = 10):
    """Wait for Ollama to be ready (important on system boot)."""
    logger.info("Waiting for Ollama to be ready...")
    for attempt in range(max_attempts):
        try:
            r = req.get("http://localhost:11434/api/tags", timeout=5)
            if r.status_code == 200:
                logger.info("Ollama is ready!")
                return True
        except Exception:
            pass
        time.sleep(interval)
        logger.info(f"  Waiting... ({(attempt+1)*interval}s)")

    logger.error("Ollama did not become ready in time.")
    return False


if __name__ == "__main__":
    if wait_for_ollama():
        asyncio.run(main())
    else:
        logger.error("Exiting — Ollama not available.")


# ─────────────────────────────────────────────
# WINDOWS TASK SCHEDULER SETUP (run once)
# ─────────────────────────────────────────────
# Open PowerShell as Administrator and run:
#
# $action  = New-ScheduledTaskAction -Execute "<YOUR_PROJECT_DIR>\assist_enve\Scripts\python.exe" `
#              -Argument "<YOUR_PROJECT_DIR>\job_finder.py" `
#              -WorkingDirectory "<YOUR_PROJECT_DIR>"
#
# $trigger = New-ScheduledTaskTrigger -AtLogOn
#
# Register-ScheduledTask -TaskName "LocalJobFinder" `
#   -Action $action -Trigger $trigger `
#   -RunLevel Highest -Force
#
# This runs job_finder.py every time you log into Windows.
# ─────────────────────────────────────────────