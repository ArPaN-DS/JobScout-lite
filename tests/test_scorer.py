import pytest
import json
from pathlib import Path
from core.scorer import _parse_scoring_response, extract_profile_keywords, keyword_prefilter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestParseScoring:
    """Tests for _parse_scoring_response — the most critical function."""

    def _load_fixtures(self):
        with open(FIXTURES_DIR / "sample_ollama_responses.json") as f:
            return json.load(f)

    def test_clean_strong_match(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["clean_strong_match"])
        assert result is not None
        assert result["match"] == "STRONG_MATCH"

    def test_clean_good_match(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["clean_good_match"])
        assert result is not None
        assert result["match"] == "GOOD_MATCH"

    def test_clean_no_match(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["clean_no_match"])
        assert result is not None
        assert result["match"] == "NO_MATCH"

    def test_with_thinking_tokens(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["with_thinking_tokens"])
        assert result is not None
        assert result["match"] == "STRONG_MATCH"

    def test_with_preamble(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["with_preamble"])
        assert result is not None
        assert result["match"] == "NO_MATCH"

    def test_legacy_numeric_high(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["legacy_numeric_score_high"])
        assert result is not None
        assert result["match"] == "STRONG_MATCH"

    def test_legacy_numeric_low(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["legacy_numeric_score_low"])
        assert result is not None
        assert result["match"] == "NO_MATCH"

    def test_empty_response_returns_none(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["empty_response"])
        assert result is None

    def test_raw_text_classification(self):
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["just_classification_word"])
        assert result is not None
        assert result["match"] == "STRONG_MATCH"

    def test_malformed_json_fallback(self):
        """Malformed JSON should fall through to text search."""
        fixtures = self._load_fixtures()
        result = _parse_scoring_response(fixtures["malformed_json"])
        assert result is not None
        assert result["match"] == "STRONG_MATCH"


class TestKeywordExtraction:
    SAMPLE_PROFILE = """# John Doe
## Target Roles
1. NLP Engineer
2. ML Engineer

## Skills
Python, PyTorch, TensorFlow, NLP, Transformers, HuggingFace, Docker

## Avoid
Sales, marketing, manual testing
"""

    def test_extracts_technical_keywords(self):
        keywords = extract_profile_keywords(self.SAMPLE_PROFILE)
        assert "python" in keywords
        assert "pytorch" in keywords
        assert "nlp" in keywords
        assert "transformers" in keywords
        assert "docker" in keywords

    def test_removes_stop_words(self):
        keywords = extract_profile_keywords(self.SAMPLE_PROFILE)
        assert "the" not in keywords
        assert "and" not in keywords
        assert "for" not in keywords

    def test_returns_set(self):
        keywords = extract_profile_keywords(self.SAMPLE_PROFILE)
        assert isinstance(keywords, set)
        assert len(keywords) > 0


class TestKeywordPrefilter:
    PROFILE_KEYWORDS = {"python", "pytorch", "nlp", "transformers", "ml", "docker"}

    def test_matching_job_passes(self):
        job = {"title": "NLP Engineer", "description": "Python and PyTorch required for NLP tasks"}
        assert keyword_prefilter(job, self.PROFILE_KEYWORDS) is True

    def test_unrelated_job_fails(self):
        job = {"title": "Sales Manager", "description": "Manage sales team and hit quarterly targets"}
        assert keyword_prefilter(job, self.PROFILE_KEYWORDS) is False

    def test_partial_match_with_min_2(self):
        job = {"title": "Data Analyst", "description": "Use Python for data analysis"}
        # Only "python" matches — should fail with min_matches=2
        assert keyword_prefilter(job, self.PROFILE_KEYWORDS, min_matches=2) is False

    def test_title_only_match(self):
        job = {"title": "ML NLP Engineer", "description": ""}
        assert keyword_prefilter(job, self.PROFILE_KEYWORDS) is True


class TestDescriptionCompression:
    def test_compress_description_strips_boilerplate(self):
        from core.scorer import compress_description
        desc = (
            "We are seeking a Python Developer.\n"
            "Equal Opportunity Employer: We value diversity and inclusion.\n"
            "Benefits include healthcare and dental plans.\n"
            "About the company: We are a top startup."
        )
        profile_kws = {"python"}
        compressed = compress_description(desc, profile_kws, max_chars=500)
        assert "Python" in compressed
        assert "Equal Opportunity" not in compressed
        assert "Benefits include" not in compressed

    def test_compress_description_prioritizes_keywords(self):
        from core.scorer import compress_description
        desc = (
            "First sentence describing the role generally.\n"
            "Second sentence describing the role generally.\n"
            "Third sentence describing the role generally.\n"
            "Fourth sentence containing Java and Spring.\n"
            "Fifth sentence containing Ruby and Rails.\n"
            "Sixth sentence containing Python and PyTorch match.\n"
            "Seventh sentence about office location."
        )
        profile_kws = {"python", "pytorch"}
        # Limit characters to force compression
        compressed = compress_description(desc, profile_kws, max_chars=200)
        assert "Python" in compressed
        assert "PyTorch" in compressed
        assert "Java" not in compressed
        assert "Ruby" not in compressed
