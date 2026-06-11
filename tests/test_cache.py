import pytest
import json
from pathlib import Path
from core.cache import JobCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    return tmp_path / "test_cache"


class TestJobCache:
    def test_fresh_cache_is_empty(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        assert cache.size == 0

    def test_mark_and_check_seen(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        job = {"title": "ML Engineer", "company": "Google"}
        assert cache.is_seen(job) is False
        cache.mark_seen(job)
        assert cache.is_seen(job) is True

    def test_persistence_across_instances(self, temp_cache_dir):
        job = {"title": "NLP Engineer", "company": "OpenAI"}

        # First instance
        cache1 = JobCache(cache_dir=temp_cache_dir)
        cache1.mark_seen(job)
        cache1._save()

        # Second instance — should load from disk
        cache2 = JobCache(cache_dir=temp_cache_dir)
        assert cache2.is_seen(job) is True

    def test_deduplicate_filters_seen_jobs(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        # Mark one job as seen
        old_job = {"title": "Old Job", "company": "OldCorp"}
        cache.mark_seen(old_job)
        cache._save()

        # Deduplicate a batch containing the old job and a new one
        jobs = [
            {"title": "Old Job", "company": "OldCorp"},
            {"title": "New Job", "company": "NewCorp"},
        ]
        novel = cache.deduplicate(jobs)
        assert len(novel) == 1
        assert novel[0]["title"] == "New Job"

    def test_deduplicate_within_batch(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        jobs = [
            {"title": "ML Engineer", "company": "Google"},
            {"title": "ML Engineer", "company": "Google"},  # duplicate
            {"title": "NLP Engineer", "company": "Meta"},
        ]
        novel = cache.deduplicate(jobs)
        assert len(novel) == 2

    def test_case_insensitive_dedup(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        jobs = [
            {"title": "ML Engineer", "company": "Google"},
            {"title": "ml engineer", "company": "google"},  # same job, different case
        ]
        novel = cache.deduplicate(jobs)
        assert len(novel) == 1

    def test_corrupted_cache_file_handled(self, temp_cache_dir):
        temp_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = temp_cache_dir / "seen_jobs.json"
        cache_file.write_text("THIS IS NOT JSON!!!", encoding="utf-8")

        # Should not crash — starts fresh
        cache = JobCache(cache_dir=temp_cache_dir)
        assert cache.size == 0
