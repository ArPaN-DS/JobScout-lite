import pytest
from core.config import load_profile, load_soul, setup_logging


class TestConfig:
    def test_setup_logging_returns_logger(self):
        log = setup_logging("test")
        assert log is not None
        assert log.name == "test"

    def test_load_profile_returns_string(self):
        profile = load_profile()
        assert isinstance(profile, str)
        assert len(profile) > 0

    def test_load_soul_returns_string(self):
        # May be empty if SOUL.md doesn't exist, but should not crash
        soul = load_soul()
        assert isinstance(soul, str)
