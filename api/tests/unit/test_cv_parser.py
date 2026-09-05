import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.cv_parser import CVParser


class TestCVParserUnit:
    """Unit tests for CVParser LLM-driven structured extraction and deterministic heuristic fallback."""

    @pytest.mark.asyncio
    async def test_parse_cv_text_with_successful_llm(self):
        mock_llm = MagicMock()
        mock_llm.generate_response = AsyncMock(
            return_value=json.dumps({
                "name": "Maria Ionescu",
                "email": "maria.ionescu@example.com",
                "phone": "+40 722 123 456",
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "experience_years": 4,
                "education": ["Computer Science, UPB"],
                "work_history": [
                    {
                        "role": "Senior Developer",
                        "company": "Tech Corp",
                        "duration": "2021 - Present",
                        "highlights": "Led backend API microservices development",
                    }
                ],
                "summary": "Experienced Python Backend Engineer.",
            })
        )

        parser = CVParser(llm_provider=mock_llm)
        raw_text = "Maria Ionescu - Experienced Python Backend Engineer with FastAPI and PostgreSQL."
        result = await parser.parse_cv_text(raw_text, "maria_ionescu.pdf")

        assert result["name"] == "Maria Ionescu"
        assert result["email"] == "maria.ionescu@example.com"
        assert "Python" in result["skills"]
        assert result["experience_years"] == 4
        assert len(result["work_history"]) == 1

    @pytest.mark.asyncio
    async def test_parse_cv_text_empty_input_raises_value_error(self):
        parser = CVParser()
        with pytest.raises(ValueError, match="Cannot parse empty resume text"):
            await parser.parse_cv_text("", "candidate.pdf")

    @pytest.mark.asyncio
    async def test_parse_cv_text_llm_failure_raises_runtime_error(self):
        mock_llm = MagicMock()
        mock_llm.generate_response = AsyncMock(side_effect=RuntimeError("Ollama connection refused"))

        parser = CVParser(llm_provider=mock_llm)
        raw_text = "Radu Popa - Email: radu.popa@dev.com"

        with pytest.raises(RuntimeError, match="LLM CV parser failed"):
            await parser.parse_cv_text(raw_text, "radu_popa_cv.pdf")

    @pytest.mark.asyncio
    async def test_parse_cv_text_invalid_structure_raises_runtime_error(self):
        mock_llm = MagicMock()
        mock_llm.generate_response = AsyncMock(return_value=json.dumps({"invalid": "data"}))

        parser = CVParser(llm_provider=mock_llm)
        raw_text = "Some resume text"

        with pytest.raises(RuntimeError, match="expected JSON object with 'name'"):
            await parser.parse_cv_text(raw_text, "test.pdf")

