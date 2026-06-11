"""
Portal scrapers for collecting job postings.
Includes LinkedIn, Indeed, Glassdoor, Naukri, Internshala, Wellfound, and Foundit.
"""

import re
import time
import random
import asyncio
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from core.config import setup_logging

logger = setup_logging("scrapers")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
]

def get_random_headers() -> dict:
    """Generate headers with rotated user agent and standard parameters."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


def search_jobspy(query: str, hours_old: int = 24) -> list[dict]:
    """Search LinkedIn, Indeed, Glassdoor via jobspy."""
    jobs = []
    try:
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
        logger.warning(f"jobspy error for '{query}': {e}")
    return jobs


def search_naukri(query: str) -> list[dict]:
    """Search Naukri.com for jobs."""
    jobs = []
    try:
        query_slug = query.replace(" ", "-").lower()
        url = f"https://www.naukri.com/{query_slug}-jobs-in-india"
        headers = get_random_headers()
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
            except Exception as e:
                logger.warning(f"Failed to parse job card on Naukri: {e}")
                continue

    except Exception as e:
        logger.warning(f"Naukri error: {e}")
    return jobs


def search_internshala(query: str) -> list[dict]:
    """Search Internshala for jobs."""
    jobs = []
    try:
        query_slug = query.replace(" ", "-").lower()
        url = f"https://internshala.com/jobs/{query_slug}-jobs"
        headers = get_random_headers()
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
            except Exception as e:
                logger.warning(f"Failed to parse job card on Internshala: {e}")
                continue

    except Exception as e:
        logger.warning(f"Internshala error: {e}")
    return jobs


def search_wellfound(query: str) -> list[dict]:
    """Search Wellfound (AngelList) for startup jobs."""
    jobs = []
    try:
        url = f"https://wellfound.com/jobs?q={query.replace(' ', '+')}&l=India"
        headers = get_random_headers()
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
                    "source":      "Wellfound [LOW_CONFIDENCE]",
                    "posted":      "Recent",
                })
    except Exception as e:
        logger.warning(f"Wellfound error: {e}")
    return jobs


def search_foundit(query: str) -> list[dict]:
    """Search Foundit.in for jobs."""
    jobs = []
    try:
        url = f"https://www.foundit.in/search/{query.replace(' ', '-').lower()}-jobs-in-india"
        headers = get_random_headers()
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
            except Exception as e:
                logger.warning(f"Failed to parse job card on Foundit: {e}")
                continue

    except Exception as e:
        logger.warning(f"Foundit error: {e}")
    return jobs


async def search_all(queries: list[str]) -> list[dict]:
    """Run all scrapers for all queries concurrently using asyncio. Returns combined job list."""
    all_jobs = []

    async def run_scraper_async(scraper_func, query, name):
        try:
            loop = asyncio.get_running_loop()
            jobs = await loop.run_in_executor(None, scraper_func, query)
            logger.info(f"  {name} for '{query}': {len(jobs)} found")
            return jobs
        except Exception as e:
            logger.warning(f"Error running {name} for '{query}': {e}")
            return []

    tasks = []
    for query in queries:
        logger.info(f"Scheduling concurrent search for: '{query}'")
        # Standard scrapers for all queries
        tasks.append(run_scraper_async(search_jobspy, query, "LinkedIn/Indeed/Glassdoor"))
        tasks.append(run_scraper_async(search_naukri, query, "Naukri"))
        tasks.append(run_scraper_async(search_internshala, query, "Internshala"))
        tasks.append(run_scraper_async(search_foundit, query, "Foundit"))

        # Wellfound only for key startup queries
        if query in ["ML Engineer", "AI Engineer", "NLP Engineer", "GenAI Engineer", "Machine Learning Engineer", "Generative AI Engineer"]:
            tasks.append(run_scraper_async(search_wellfound, query, "Wellfound"))

    # Execute all scraper queries concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        if isinstance(res, list):
            all_jobs.extend(res)
        elif isinstance(res, Exception):
            logger.warning(f"Scraper task execution failed with exception: {res}")

    logger.info(f"Total collected: {len(all_jobs)} jobs from all portals")
    return all_jobs
