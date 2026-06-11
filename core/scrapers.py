"""
Portal scrapers for collecting job postings.
Includes LinkedIn, Indeed, Glassdoor, Naukri, Internshala, Wellfound, and Foundit.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from core.config import setup_logging

logger = setup_logging("scrapers")


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
            except Exception as e:
                logger.warning(f"Failed to parse job card on Foundit: {e}")
                continue

    except Exception as e:
        logger.warning(f"Foundit error: {e}")
    return jobs


def search_all(queries: list[str]) -> list[dict]:
    """Run all scrapers for all queries. Returns combined job list."""
    all_jobs = []

    for idx, query in enumerate(queries):
        logger.info(f"[{idx+1}/{len(queries)}] Searching: '{query}'")

        # jobspy (LinkedIn, Indeed, Glassdoor)
        jobs = search_jobspy(query, hours_old=24)
        logger.info(f"  LinkedIn/Indeed/Glassdoor: {len(jobs)} found")
        all_jobs.extend(jobs)

        # Naukri
        jobs = search_naukri(query)
        logger.info(f"  Naukri: {len(jobs)} found")
        all_jobs.extend(jobs)

        # Internshala
        jobs = search_internshala(query)
        logger.info(f"  Internshala: {len(jobs)} found")
        all_jobs.extend(jobs)

        # Foundit
        jobs = search_foundit(query)
        logger.info(f"  Foundit: {len(jobs)} found")
        all_jobs.extend(jobs)

        # Wellfound (only for key queries)
        if query in ["ML Engineer", "AI Engineer", "NLP Engineer", "GenAI Engineer"]:
            jobs = search_wellfound(query)
            logger.info(f"  Wellfound: {len(jobs)} found")
            all_jobs.extend(jobs)

        # Be polite to servers
        time.sleep(2)

    logger.info(f"Total collected: {len(all_jobs)} jobs from all portals")
    return all_jobs
