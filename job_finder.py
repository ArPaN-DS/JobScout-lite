"""
╔══════════════════════════════════════════════════════════════╗
║           ARPAN'S AI JOB FINDER — job_finder.py             ║
║  Searches all portals → Scores with Ollama → Sends Telegram ║
╚══════════════════════════════════════════════════════════════╝

SETUP (run once in PowerShell):
  cd C:\assistant
  .\assist_enve\Scripts\activate
  pip install python-jobspy requests beautifulsoup4 httpx python-telegram-bot

USAGE:
  python job_finder.py

AUTO-START: Add to Windows Task Scheduler (instructions at bottom)
"""

import asyncio
import httpx
import json
import time
import re
import os
from datetime import datetime, timedelta
from typing import Optional

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION — READ FROM .ENV
# ─────────────────────────────────────────────

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OLLAMA_URL      = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen3:4b")
MATCH_THRESHOLD = 60                          # Only send jobs 60%+ match

# ─────────────────────────────────────────────
# ARPAN'S FULL PROFILE (used for matching)
# ─────────────────────────────────────────────

ARPAN_PROFILE = """
Name: Arpan Majumdar
Role: ML/NLP/AI Engineer (Fresher/Early Career)
Location: West Bengal, India — open to remote & relocation

EDUCATION:
- M.Sc. Data Science, University of Kalyani (2023-2025), CGPA: 7.75
- B.Sc. Computer Science, Memari College (2020-2023), CGPA: 9.1

PUBLICATIONS & ACHIEVEMENTS:
- ACL 2025 (SemEval), Vienna — Ranked 22nd globally (50+ teams)
- CLEF 2025 (CheckThat!), Madrid — Ranked 9th globally, Macro F1=0.8262
- DRDO-Funded research (under review) — 86.08% accuracy
- NeuroHack 2026 at IIT Guwahati — Rank 34

TARGET ROLES (in priority):
1. ML Engineer
2. AI Engineer
3. GenAI/Generative AI Engineer
4. NLP Engineer / NLP Researcher
5. Data Scientist
6. Speech AI Engineer
7. AI Research Engineer

KEY TECHNICAL SKILLS:
- PyTorch, TensorFlow, Hugging Face Transformers, Scikit-learn
- WavLM, ECAPA-TDNN, Wav2Vec2, Whisper (Speech AI)
- BERT, XLM-RoBERTa, GPT-4o, Gemini, LLaMA3, Qwen, DeepSeek
- RAG, FAISS, Milvus, LangChain, ReAct Agents
- Django, FastAPI, Flask, WebSockets, REST APIs
- Docker, AWS, MLflow, Linux
- Fine-tuning, LoRA/QLoRA, Multi-task Learning, AMP

EXPERIENCE:
- 2+ years production AI systems (speech, NLP, GenAI, MLOps)
- Audio deepfake detection (multi-task WavLM model)
- Forensic speaker recognition system (ECAPA-TDNN)
- Neuro-symbolic agentic RAG pipeline
- Real-time multimodal meeting AI
- Credit risk scoring (R²=97.7%)
- LLM-powered data extraction pipelines

AVOID: Sales, marketing, non-technical, data entry, no-AI roles
"""

# ─────────────────────────────────────────────
# JOB SEARCH QUERIES
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# TOP AI COMPANY CAREER PAGES (India-focused)
# ─────────────────────────────────────────────

COMPANY_CAREER_PAGES = [
    {"name": "Sarvam AI",         "url": "https://www.sarvam.ai/careers"},
    {"name": "Krutrim",            "url": "https://krutrim.com/careers"},
    {"name": "Haptik",             "url": "https://haptik.ai/careers"},
    {"name": "Vernacular.ai",      "url": "https://vernacular.ai/careers"},
    {"name": "Yellow.ai",          "url": "https://yellow.ai/company/careers"},
    {"name": "Murf AI",            "url": "https://murf.ai/careers"},
    {"name": "Uniphore",           "url": "https://www.uniphore.com/company/careers"},
    {"name": "Mad Street Den",     "url": "https://www.madstreetden.com/careers"},
    {"name": "Observe.AI",         "url": "https://www.observe.ai/company/careers"},
    {"name": "Sprinklr",           "url": "https://www.sprinklr.com/careers"},
    {"name": "Fractal Analytics",  "url": "https://fractal.ai/careers"},
    {"name": "Sigmoid",            "url": "https://www.sigmoid.com/careers"},
    {"name": "Tiger Analytics",    "url": "https://www.tigeranalytics.com/careers"},
    {"name": "Saama Technologies", "url": "https://www.saama.com/careers"},
    {"name": "Nference",           "url": "https://nference.com/careers"},
]

# ─────────────────────────────────────────────
# PORTAL SCRAPERS
# ─────────────────────────────────────────────

def search_jobspy(query: str, hours_old: int = 24) -> list[dict]:
    """Search LinkedIn, Indeed, Glassdoor via jobspy."""
    jobs = []
    try:
        from jobspy import scrape_jobs
        results = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=query,
            location="India",
            results_wanted=20,
            hours_old=hours_old,
            country_indeed="India",
        )
        for _, row in results.iterrows():
            if row.get("job_url") and row.get("title"):
                jobs.append({
                    "title":       str(row.get("title", "")),
                    "company":     str(row.get("company", "Unknown")),
                    "location":    str(row.get("location", "India")),
                    "description": str(row.get("description", ""))[:2000],
                    "apply_url":   str(row.get("job_url", "")),
                    "source":      str(row.get("site", "jobspy")),
                    "posted":      str(row.get("date_posted", "Recent")),
                })
    except Exception as e:
        print(f"  ⚠️  jobspy error for '{query}': {e}")
    return jobs


def search_naukri(query: str) -> list[dict]:
    """Search Naukri.com for jobs."""
    jobs = []
    try:
        import requests
        from bs4 import BeautifulSoup

        query_slug = query.replace(" ", "-").lower()
        url = f"https://www.naukri.com/{query_slug}-jobs-in-india"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return jobs

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("article", class_=re.compile("jobTuple|job-tuple"), limit=10)

        for card in cards:
            try:
                title_el = card.find(["a", "h2"], class_=re.compile("title|jobTitle"))
                comp_el  = card.find(class_=re.compile("company|companyInfo"))
                loc_el   = card.find(class_=re.compile("location|loc"))
                link_el  = card.find("a", href=True)

                title   = title_el.get_text(strip=True) if title_el else ""
                company = comp_el.get_text(strip=True)  if comp_el  else "Unknown"
                location = loc_el.get_text(strip=True)  if loc_el   else "India"
                link    = link_el["href"]                if link_el  else ""

                if title and link:
                    if not link.startswith("http"):
                        link = "https://www.naukri.com" + link
                    jobs.append({
                        "title":       title,
                        "company":     company,
                        "location":    location,
                        "description": f"{title} at {company}",
                        "apply_url":   link,
                        "source":      "Naukri",
                        "posted":      "Recent",
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"  ⚠️  Naukri error: {e}")
    return jobs


def search_internshala(query: str) -> list[dict]:
    """Search Internshala for jobs."""
    jobs = []
    try:
        import requests
        from bs4 import BeautifulSoup

        query_slug = query.replace(" ", "-").lower()
        url = f"https://internshala.com/jobs/{query_slug}-jobs"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return jobs

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("div", class_=re.compile("individual_internship|job-card"), limit=10)

        for card in cards:
            try:
                title_el = card.find(class_=re.compile("job-title|profile"))
                comp_el  = card.find(class_=re.compile("company-name"))
                link_el  = card.find("a", href=True)

                title   = title_el.get_text(strip=True) if title_el else ""
                company = comp_el.get_text(strip=True)  if comp_el  else "Unknown"
                link    = link_el["href"]                if link_el  else ""

                if title and link:
                    if not link.startswith("http"):
                        link = "https://internshala.com" + link
                    jobs.append({
                        "title":       title,
                        "company":     company,
                        "location":    "India",
                        "description": f"{title} at {company}",
                        "apply_url":   link,
                        "source":      "Internshala",
                        "posted":      "Recent",
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"  ⚠️  Internshala error: {e}")
    return jobs


def search_wellfound(query: str) -> list[dict]:
    """Search Wellfound (AngelList) for startup jobs."""
    jobs = []
    try:
        import requests
        query_slug = query.replace(" ", "-").lower()
        url = f"https://wellfound.com/jobs?q={query.replace(' ', '+')}&l=India"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        # Wellfound is JS-heavy — add basic fallback
        if "job" in r.text.lower() and r.status_code == 200:
            # Try to find job links
            links = re.findall(r'href="(/jobs/[^"]+)"', r.text)
            for link in links[:10]:
                full_url = f"https://wellfound.com{link}"
                title = link.split("/")[-1].replace("-", " ").title()
                jobs.append({
                    "title":       title,
                    "company":     "Startup (Wellfound)",
                    "location":    "India / Remote",
                    "description": f"{query} role at startup",
                    "apply_url":   full_url,
                    "source":      "Wellfound",
                    "posted":      "Recent",
                })
    except Exception as e:
        print(f"  ⚠️  Wellfound error: {e}")
    return jobs


def search_foundit(query: str) -> list[dict]:
    """Search Foundit.in for jobs."""
    jobs = []
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://www.foundit.in/search/{query.replace(' ', '-').lower()}-jobs-in-india"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return jobs

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("div", class_=re.compile("card|job-item"), limit=10)

        for card in cards:
            try:
                title_el = card.find(["h2", "h3", "a"], class_=re.compile("title|position"))
                comp_el  = card.find(class_=re.compile("company"))
                link_el  = card.find("a", href=True)

                title   = title_el.get_text(strip=True) if title_el else ""
                company = comp_el.get_text(strip=True)  if comp_el  else "Unknown"
                link    = link_el["href"]                if link_el  else ""

                if title and link:
                    if not link.startswith("http"):
                        link = "https://www.foundit.in" + link
                    jobs.append({
                        "title":       title,
                        "company":     company,
                        "location":    "India",
                        "description": f"{title} at {company}",
                        "apply_url":   link,
                        "source":      "Foundit",
                        "posted":      "Recent",
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"  ⚠️  Foundit error: {e}")
    return jobs


# ─────────────────────────────────────────────
# OLLAMA MATCH SCORER
# ─────────────────────────────────────────────

async def score_job_match(job: dict, client: httpx.AsyncClient) -> int:
    """Ask Ollama to score job match against Arpan's profile. Returns 0-100."""
    prompt = f"""You are a job matching assistant. Score how well this job matches the candidate profile.

CANDIDATE PROFILE:
{ARPAN_PROFILE}

JOB:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Description: {job['description'][:1000]}

Reply with ONLY a JSON object like this: {{"score": 75, "reason": "Strong NLP match"}}
Score 0-100. Be strict. Score above 60 only if the job genuinely matches the candidate's ML/NLP/AI skills."""

    try:
        response = await client.post(OLLAMA_URL, json={
            "model":  OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096, "num_thread": 4}
        }, timeout=120.0)

        content = response.json()["message"]["content"]
        # Extract JSON from response
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            data  = json.loads(json_match.group())
            score = int(data.get("score", 0))
            job["match_reason"] = data.get("reason", "")
            return min(100, max(0, score))
    except Exception as e:
        print(f"  ⚠️  Scoring error for '{job['title']}': {e}")
    return 0


# ─────────────────────────────────────────────
# DEDUPLICATION
# ─────────────────────────────────────────────

def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Remove duplicate jobs based on title + company similarity."""
    seen    = set()
    unique  = []
    for job in jobs:
        key = f"{job['title'].lower().strip()[:40]}_{job['company'].lower().strip()[:30]}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ─────────────────────────────────────────────
# TELEGRAM SENDER
# ─────────────────────────────────────────────

async def send_telegram(message: str):
    """Send message to Telegram."""
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_TOKEN)
        # Split if too long
        chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
        for chunk in chunks:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=chunk,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ─────────────────────────────────────────────
# MAIN JOB FINDER
# ─────────────────────────────────────────────

async def main():
    start_time = datetime.now()
    last_progress_time = [datetime.now()]  # mutable for nested function

    print(f"\n{'='*60}")
    print(f"  🔍 ARPAN'S JOB FINDER — {start_time.strftime('%d %b %Y, %I:%M %p')}")
    print(f"{'='*60}\n")

    async def maybe_send_progress(message: str):
        """Send progress update if 5 minutes have passed."""
        now = datetime.now()
        if (now - last_progress_time[0]).seconds >= 300:
            elapsed = (now - start_time).seconds // 60
            await send_telegram(
                f"⏳ <b>Progress Update</b>\n"
                f"{message}\n"
                f"🕐 Running for: <b>{elapsed} min</b>"
            )
            last_progress_time[0] = now

    # Send start notification
    await send_telegram(
        f"🔍 <b>Job Finder Started</b>\n"
        f"📅 {start_time.strftime('%d %b %Y, %I:%M %p')}\n"
        f"🎯 Scanning: LinkedIn, Indeed, Naukri, Internshala, Wellfound, Foundit\n"
        f"⏳ Progress updates every 5 min. Full results in ~45-60 min."
    )

    # ── STEP 1: Collect all jobs ──────────────────────────────
    print("📡 STEP 1: Collecting jobs from all portals...")
    all_jobs = []

    for idx, query in enumerate(SEARCH_QUERIES):
        print(f"\n  🔎 Searching: '{query}'")

        # jobspy (LinkedIn, Indeed, Glassdoor)
        print(f"     LinkedIn/Indeed/Glassdoor...", end=" ")
        jobs = search_jobspy(query, hours_old=24)
        print(f"{len(jobs)} found")
        all_jobs.extend(jobs)

        # Naukri
        print(f"     Naukri...", end=" ")
        jobs = search_naukri(query)
        print(f"{len(jobs)} found")
        all_jobs.extend(jobs)

        # Internshala
        print(f"     Internshala...", end=" ")
        jobs = search_internshala(query)
        print(f"{len(jobs)} found")
        all_jobs.extend(jobs)

        # Foundit
        print(f"     Foundit...", end=" ")
        jobs = search_foundit(query)
        print(f"{len(jobs)} found")
        all_jobs.extend(jobs)

        # Wellfound (only for key queries)
        if query in ["ML Engineer", "AI Engineer", "NLP Engineer", "GenAI Engineer"]:
            print(f"     Wellfound...", end=" ")
            jobs = search_wellfound(query)
            print(f"{len(jobs)} found")
            all_jobs.extend(jobs)

        # Progress update every 5 min during collection
        await maybe_send_progress(
            f"📡 <b>Collecting jobs...</b>\n"
            f"Queries done: <b>{idx+1}/{len(SEARCH_QUERIES)}</b>\n"
            f"Jobs collected so far: <b>{len(all_jobs)}</b>"
        )

        time.sleep(2)  # Be polite to servers

    print(f"\n  ✅ Total collected: {len(all_jobs)} jobs")

    # ── STEP 2: Deduplicate ───────────────────────────────────
    print("\n🧹 STEP 2: Deduplicating...")
    all_jobs = deduplicate_jobs(all_jobs)
    print(f"  ✅ After dedup: {len(all_jobs)} unique jobs")

    # Always send collection summary
    await send_telegram(
        f"📦 <b>Collection Complete!</b>\n"
        f"Unique jobs to score: <b>{len(all_jobs)}</b>\n"
        f"🧠 Now scoring each job with {OLLAMA_MODEL}...\n"
        f"Updates every 5 min."
    )
    last_progress_time[0] = datetime.now()  # Reset for scoring phase

    # ── STEP 3: Score with Ollama ─────────────────────────────
    print(f"\n🧠 STEP 3: Scoring {len(all_jobs)} jobs with {OLLAMA_MODEL}...")
    print("  (This takes the longest — each job scored individually)\n")

    matched_jobs = []
    errors = 0
    async with httpx.AsyncClient() as client:
        for i, job in enumerate(all_jobs):
            print(f"  [{i+1}/{len(all_jobs)}] Scoring: {job['title']} @ {job['company'][:30]}...", end=" ")
            score = await score_job_match(job, client)
            job["match_score"] = score
            if score == 0 and "match_reason" not in job:
                errors += 1
            print(f"→ {score}%")

            if score >= MATCH_THRESHOLD:
                matched_jobs.append(job)

            # Progress update every 5 min during scoring
            await maybe_send_progress(
                f"🧠 <b>Scoring in progress...</b>\n"
                f"Scored: <b>{i+1}/{len(all_jobs)}</b> jobs\n"
                f"Matched so far (>={MATCH_THRESHOLD}%): <b>{len(matched_jobs)}</b>\n"
                f"Errors: {errors}"
            )

    # Sort by score descending
    matched_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    print(f"\n  ✅ Matched jobs (≥{MATCH_THRESHOLD}%): {len(matched_jobs)}")

    # ── STEP 4: Send to Telegram ──────────────────────────────
    print("\n📱 STEP 4: Sending results to Telegram...")
    elapsed = (datetime.now() - start_time).seconds // 60

    if not matched_jobs:
        await send_telegram(
            f"😕 <b>No matches found today</b>\n"
            f"Scanned {len(all_jobs)} jobs, none scored ≥{MATCH_THRESHOLD}%.\n"
            f"Try again tomorrow or lower the threshold."
        )
        print("  No matches found.")
        return

    # Header message
    await send_telegram(
        f"✅ <b>Job Scan Complete!</b>\n"
        f"📊 Scanned: <b>{len(all_jobs)}</b> jobs\n"
        f"🎯 Matched (≥{MATCH_THRESHOLD}%): <b>{len(matched_jobs)}</b> jobs\n"
        f"⏱️ Time taken: <b>{elapsed} min</b>\n"
        f"📅 {start_time.strftime('%d %b %Y')}\n\n"
        f"👇 <b>Here are your matches, ranked by fit:</b>"
    )

    # Send each matched job
    for i, job in enumerate(matched_jobs[:30], 1):  # Max 30 jobs
        score = job["match_score"]
        emoji = "🟢" if score >= 80 else "🟡" if score >= 70 else "🔵"

        msg = (
            f"{emoji} <b>#{i} — {score}% Match</b>\n"
            f"💼 <b>{job['title']}</b>\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"🌐 {job['source']}\n"
            f"💡 {job.get('match_reason', '')}\n"
            f"🔗 <a href='{job['apply_url']}'>Apply Here</a>"
        )
        await send_telegram(msg)
        await asyncio.sleep(0.3)

    # Footer
    await send_telegram(
        f"🏁 <b>That's all for today!</b>\n"
        f"Next scan: tomorrow at startup.\n"
        f"Reply <b>/scan</b> anytime to trigger a fresh scan."
    )

    print(f"\n{'='*60}")
    print(f"  ✅ Done! Sent {len(matched_jobs[:30])} jobs to Telegram")
    print(f"  ⏱️  Total time: {elapsed} minutes")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Wait for Ollama to be ready (important on startup)
    print("⏳ Waiting for Ollama to be ready...")
    import requests as req
    for attempt in range(12):  # Wait up to 2 minutes
        try:
            r = req.get("http://localhost:11434/api/tags", timeout=5)
            if r.status_code == 200:
                print("✅ Ollama is ready!\n")
                break
        except Exception:
            pass
        time.sleep(10)
        print(f"  Waiting... ({(attempt+1)*10}s)")

    asyncio.run(main())


# ─────────────────────────────────────────────
# WINDOWS TASK SCHEDULER SETUP (run once)
# ─────────────────────────────────────────────
# Open PowerShell as Administrator and run:
#
# $action  = New-ScheduledTaskAction -Execute "C:\assistant\assist_enve\Scripts\python.exe" `
#              -Argument "C:\assistant\job_finder.py" `
#              -WorkingDirectory "C:\assistant"
#
# $trigger = New-ScheduledTaskTrigger -AtLogOn
#
# Register-ScheduledTask -TaskName "ArpanJobFinder" `
#   -Action $action -Trigger $trigger `
#   -RunLevel Highest -Force
#
# This runs job_finder.py every time you log into Windows.
# ─────────────────────────────────────────────