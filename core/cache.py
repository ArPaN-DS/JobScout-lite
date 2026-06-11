"""
Persistent deduplication cache for job listings.
Stores seen job hashes as a JSON file so duplicates are filtered across runs.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from core.config import CACHE_DIR, setup_logging

logger = setup_logging("cache")


class JobCache:
    """Manages a persistent set of seen job hashes with optional expiry."""

    def __init__(self, cache_dir: Optional[Path] = None, expiry_days: int = 30):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "seen_jobs.json"
        self.expiry_days = expiry_days
        self._cache: dict[str, dict] = {}  # hash -> metadata dict
        self._load()

    def _load(self):
        """Load existing cache from disk and perform migrations."""
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                # Handle old formats: list of hashes
                if isinstance(data, list):
                    self._cache = {
                        h: {
                            "date": datetime.now().isoformat(),
                            "state": "seen",
                            "feedback": "none",
                            "title": "",
                            "company": "",
                            "description": ""
                        } for h in data
                    }
                    logger.info(f"Migrated {len(self._cache)} entries from list-based cache")
                elif isinstance(data, dict):
                    # Migrate old dict formats (hash -> date_string) to (hash -> metadata_dict)
                    self._cache = {}
                    for h, v in data.items():
                        if isinstance(v, str):
                            self._cache[h] = {
                                "date": v,
                                "state": "seen",
                                "feedback": "none",
                                "title": "",
                                "company": "",
                                "description": ""
                            }
                        elif isinstance(v, dict):
                            self._cache[h] = {
                                "date": v.get("date", datetime.now().isoformat()),
                                "state": v.get("state", "seen"),
                                "feedback": v.get("feedback", "none"),
                                "title": v.get("title", ""),
                                "company": v.get("company", ""),
                                "description": v.get("description", "")
                            }
                        else:
                            self._cache[h] = {
                                "date": datetime.now().isoformat(),
                                "state": "seen",
                                "feedback": "none",
                                "title": "",
                                "company": "",
                                "description": ""
                            }
                else:
                    self._cache = {}
                logger.info(f"Loaded {len(self._cache)} cached job entries")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Cache file corrupted, starting fresh: {e}")
                self._cache = {}
        else:
            logger.info("No existing cache found, starting fresh")

    def _save(self):
        """Persist cache to disk."""
        self.cache_file.write_text(
            json.dumps(self._cache, indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _make_key(job: dict) -> str:
        """Generate a stable hash key from job title + company."""
        raw = f"{job.get('title', '').lower().strip()}|{job.get('company', '').lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def is_seen(self, job: dict) -> bool:
        """Check if a job has been seen before."""
        return self._make_key(job) in self._cache

    def mark_seen(self, job: dict, state: str = "seen"):
        """Mark a job as seen with metadata."""
        self._cache[self._make_key(job)] = {
            "date": datetime.now().isoformat(),
            "state": state,
            "feedback": "none",
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "description": job.get("description", "")
        }

    def deduplicate(self, jobs: list[dict]) -> list[dict]:
        """
        Filter out previously seen jobs AND deduplicate within the batch.
        Returns only novel jobs. Marks all returned jobs as seen.
        """
        novel = []
        batch_seen = set()

        for job in jobs:
            key = self._make_key(job)
            if key not in self._cache and key not in batch_seen:
                batch_seen.add(key)
                novel.append(job)
                self.mark_seen(job)

        logger.info(
            f"Deduplication: {len(jobs)} input → {len(novel)} novel "
            f"({len(jobs) - len(novel)} duplicates removed)"
        )
        self._save()
        return novel

    def cleanup_expired(self):
        """Remove entries older than expiry_days."""
        cutoff = datetime.now() - timedelta(days=self.expiry_days)
        before = len(self._cache)
        self._cache = {
            k: v for k, v in self._cache.items()
            if datetime.fromisoformat(v.get("date", datetime.now().isoformat())) > cutoff
        }
        removed = before - len(self._cache)
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")
            self._save()

    def find_key_by_short_id(self, short_id: str) -> Optional[str]:
        """Resolve a 6-character short hash ID back to its full 16-character cache key."""
        short_id = short_id.lower().strip()
        for key in self._cache:
            if key.startswith(short_id):
                return key
        return None

    def set_feedback(self, short_id: str, feedback: str) -> bool:
        """Set feedback ('like' or 'dislike') for a job using its 6-character short ID."""
        key = self.find_key_by_short_id(short_id)
        if key:
            self._cache[key]["feedback"] = feedback
            self._save()
            return True
        return False

    def set_state(self, short_id: str, state: str) -> bool:
        """Set state (e.g. 'notified', 'applied', 'archived') for a job using its 6-character short ID."""
        key = self.find_key_by_short_id(short_id)
        if key:
            self._cache[key]["state"] = state
            self._save()
            return True
        return False

    def get_feedback_exemplars(self) -> list[dict]:
        """Retrieve all historical jobs that have positive ('like') or negative ('dislike') feedback."""
        exemplars = []
        for key, data in self._cache.items():
            if data.get("feedback") in ("like", "dislike"):
                exemplars.append({
                    "title": data.get("title", ""),
                    "company": data.get("company", ""),
                    "description": data.get("description", ""),
                    "feedback": data.get("feedback", "")
                })
        return exemplars

    def get_applied_jobs(self) -> list[dict]:
        """Retrieve all jobs marked as applied."""
        applied = []
        for key, data in self._cache.items():
            if data.get("state") == "applied":
                applied.append({
                    "key": key,
                    "title": data.get("title", ""),
                    "company": data.get("company", ""),
                    "date": data.get("date", "")
                })
        return applied

    @property
    def size(self) -> int:
        return len(self._cache)


def load_chat_history() -> dict[int, list[dict]]:
    """Load persistent conversation history from disk."""
    history_file = CACHE_DIR / "chat_history.json"
    if history_file.exists():
        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            return {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Could not load chat history, returning empty: {e}")
            return {}
    return {}


def save_chat_history(history: dict):
    """Save persistent conversation history to disk."""
    history_file = CACHE_DIR / "chat_history.json"
    try:
        data = {str(k): v for k, v in history.items()}
        history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to save chat history: {e}")
