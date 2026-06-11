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
        self._cache: dict[str, str] = {}  # hash -> ISO date string
        self._load()

    def _load(self):
        """Load existing cache from disk."""
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                # Handle both old format (list of hashes) and new format (dict with dates)
                if isinstance(data, list):
                    # Migrate from old format
                    self._cache = {h: datetime.now().isoformat() for h in data}
                    logger.info(f"Migrated {len(self._cache)} entries from old cache format")
                elif isinstance(data, dict):
                    self._cache = data
                else:
                    self._cache = {}
                logger.info(f"Loaded {len(self._cache)} cached job hashes")
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

    def mark_seen(self, job: dict):
        """Mark a job as seen with current timestamp."""
        self._cache[self._make_key(job)] = datetime.now().isoformat()

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
            if datetime.fromisoformat(v) > cutoff
        }
        removed = before - len(self._cache)
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")
            self._save()

    @property
    def size(self) -> int:
        return len(self._cache)
