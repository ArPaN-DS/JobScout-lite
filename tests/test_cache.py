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

    def test_short_id_resolution(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        job = {"title": "Fullstack Developer", "company": "TechCorp"}
        cache.mark_seen(job)
        full_key = cache._make_key(job)
        short_id = full_key[:6]

        resolved = cache.find_key_by_short_id(short_id)
        assert resolved == full_key

        non_existent = cache.find_key_by_short_id("z1y2x3")
        assert non_existent is None

    def test_feedback_loop(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        job = {"title": "Backend Lead", "company": "SystemCorp", "description": "Django, Postgres"}
        cache.mark_seen(job)
        short_id = cache._make_key(job)[:6]

        # Set feedback
        success = cache.set_feedback(short_id, "like")
        assert success is True
        
        exemplars = cache.get_feedback_exemplars()
        assert len(exemplars) == 1
        assert exemplars[0]["title"] == "Backend Lead"
        assert exemplars[0]["feedback"] == "like"

    def test_state_updates(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        job = {"title": "Frontend dev", "company": "Startup"}
        cache.mark_seen(job)
        short_id = cache._make_key(job)[:6]

        assert cache.set_state(short_id, "applied") is True
        applied = cache.get_applied_jobs()
        assert len(applied) == 1
        assert applied[0]["title"] == "Frontend dev"

    def test_persistent_chat_history(self, monkeypatch, tmp_path):
        from core.cache import load_chat_history, save_chat_history
        # Mock CACHE_DIR
        monkeypatch.setattr("core.cache.CACHE_DIR", tmp_path)

        dummy_history = {12345: [{"role": "user", "content": "hello"}]}
        save_chat_history(dummy_history)

        loaded = load_chat_history()
        assert 12345 in loaded
        assert loaded[12345][0]["content"] == "hello"

    def test_reasoned_feedback_loop(self, temp_cache_dir):
        cache = JobCache(cache_dir=temp_cache_dir)
        job = {"title": "Backend Lead", "company": "SystemCorp", "description": "Django, Postgres"}
        cache.mark_seen(job)
        short_id = cache._make_key(job)[:6]

        # Set feedback with reason
        success = cache.set_feedback(short_id, "dislike", "Django")
        assert success is True

        exemplars = cache.get_feedback_exemplars()
        assert len(exemplars) == 1
        assert exemplars[0]["title"] == "Backend Lead"
        assert exemplars[0]["feedback"] == "dislike"
        assert exemplars[0]["feedback_reason"] == "Django"
