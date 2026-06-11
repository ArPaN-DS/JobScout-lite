import pytest
from core.notifier import format_job_message, is_authorized_chat


class TestFormatJobMessage:
    def test_formats_strong_match(self):
        job = {
            "title": "NLP Engineer",
            "company": "Google",
            "location": "Bangalore",
            "source": "LinkedIn",
            "match_tier": "STRONG_MATCH",
            "match_reason": "Direct NLP role",
            "apply_url": "https://example.com/apply",
        }
        msg = format_job_message(job, rank=1)
        assert "🟢" in msg
        assert "#1" in msg
        assert "NLP Engineer" in msg
        assert "Google" in msg
        assert "Apply Here" in msg

    def test_formats_good_match(self):
        job = {
            "title": "ML Engineer",
            "company": "Meta",
            "location": "Remote",
            "source": "Indeed",
            "match_tier": "GOOD_MATCH",
            "match_reason": "Related ML role",
            "apply_url": "https://example.com",
        }
        msg = format_job_message(job, rank=5)
        assert "🟡" in msg
        assert "#5" in msg

    def test_handles_missing_fields(self):
        job = {"title": "Test Job", "match_tier": "SKIP"}
        msg = format_job_message(job, rank=1)
        assert "Test Job" in msg
        assert "Unknown" in msg  # fallback for missing company/location

    def test_includes_tailored_pitch(self):
        job = {
            "title": "NLP Engineer",
            "match_tier": "STRONG_MATCH",
            "tailored_pitch": "I am a strong candidate because of my NLP expertise."
        }
        msg = format_job_message(job, rank=1)
        assert "Personalized Application Pitch" in msg
        assert "I am a strong candidate because of my NLP expertise." in msg


class TestAuthorization:
    def test_authorized_chat_passes(self, monkeypatch):
        monkeypatch.setattr("core.notifier.TELEGRAM_CHAT_ID", "12345")
        assert is_authorized_chat(12345) is True
        assert is_authorized_chat("12345") is True

    def test_unauthorized_chat_fails(self, monkeypatch):
        monkeypatch.setattr("core.notifier.TELEGRAM_CHAT_ID", "12345")
        assert is_authorized_chat(99999) is False

    def test_no_chat_id_configured_fails(self, monkeypatch):
        monkeypatch.setattr("core.notifier.TELEGRAM_CHAT_ID", None)
        assert is_authorized_chat(12345) is False
