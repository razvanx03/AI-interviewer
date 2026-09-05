import unicodedata
import pytest
from core.constants import (
    sanitize_postgres_text,
    TECH_CATALOGUE,
    BASE_SCREENING_SCORE,
    MAX_SCREENING_SCORE,
    CLARIFICATION_STEER_THRESHOLD,
    INTERVIEW_COMPLETE_TOKEN,
)


class TestConstantsAndSanitizer:
    """Unit tests for string sanitization and constant invariants."""

    def test_sanitize_postgres_text_empty_and_none(self):
        assert sanitize_postgres_text(None) == ""
        assert sanitize_postgres_text("") == ""
        assert sanitize_postgres_text("   ") == ""

    def test_sanitize_postgres_text_null_bytes(self):
        # 0x00 null bytes must be stripped
        raw = "Hello\x00World\x00! This is a test \x00."
        sanitized = sanitize_postgres_text(raw)
        assert "\x00" not in sanitized
        assert sanitized == "HelloWorld! This is a test ."

    def test_sanitize_postgres_text_preserves_allowed_whitespace(self):
        # Newlines, carriage returns, and tabs must be preserved
        raw = "Line 1\nLine 2\r\nLine 3\tTabbed"
        sanitized = sanitize_postgres_text(raw)
        assert "Line 1\nLine 2\r\nLine 3\tTabbed" == sanitized

    def test_sanitize_postgres_text_removes_control_characters(self):
        # ASCII control characters (0x01-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f-0x9f) replaced
        raw = "Test\x01\x02Control\x08Chars\x1fAnd\x7fDel"
        sanitized = sanitize_postgres_text(raw)
        assert "\x01" not in sanitized
        assert "\x08" not in sanitized
        assert "\x1f" not in sanitized
        assert "\x7f" not in sanitized
        assert "Test" in sanitized and "Control" in sanitized

    def test_sanitize_postgres_text_normalizes_unicode_nfc(self):
        # Decomposed Unicode (NFD: 'e' + combining acute accent) normalized to NFC ('é')
        decomposed = "e\u0301"  # NFD
        precomposed = "\u00e9"  # NFC: 'é'
        assert decomposed != precomposed
        sanitized = sanitize_postgres_text(decomposed)
        assert sanitized == precomposed
        assert unicodedata.is_normalized("NFC", sanitized)

    def test_tech_catalogue_completeness(self):
        assert len(TECH_CATALOGUE) >= 25
        # Core technologies must be present
        required_techs = [".NET", "C#", "Python", "React", "Docker", "PostgreSQL", "FastAPI", "TypeScript"]
        for tech in required_techs:
            assert tech in TECH_CATALOGUE

    def test_constants_invariants(self):
        assert BASE_SCREENING_SCORE > 0
        assert MAX_SCREENING_SCORE <= 100
        assert BASE_SCREENING_SCORE < MAX_SCREENING_SCORE
        assert CLARIFICATION_STEER_THRESHOLD >= 2
        assert INTERVIEW_COMPLETE_TOKEN == "[INTERVIEW_COMPLETE]"

