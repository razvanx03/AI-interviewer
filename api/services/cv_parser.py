import json
import logging
from typing import Dict, Any, Optional
from llm import get_llm_provider, BaseLLMProvider
from core.config import settings

logger = logging.getLogger("api.services.cv_parser")

CV_PARSER_SYSTEM_PROMPT = """You are an expert HR Data Scientist and Resume Parser.
Your task is to analyze the provided raw CV text and extract structured information in strictly valid JSON format.

JSON Output Schema:
{
  "name": "Candidate Full Name",
  "email": "candidate.email@example.com",
  "phone": "+1 234 567 8900",
  "skills": ["Skill 1", "Skill 2", "Skill 3"],
  "experience_years": 4,
  "education": ["Degree in Computer Science, University Name"],
  "work_history": [
    {
      "role": "Job Title",
      "company": "Company Name",
      "duration": "2021 - Present",
      "highlights": "Key achievements and responsibilities"
    }
  ],
  "summary": "Professional summary of candidate's background and core competencies."
}

Rules:
1. Output valid JSON ONLY. No explanation or surrounding text.
2. If a field is not found in the resume, use null for strings/numbers and [] for lists.
"""

class CVParser:
    """
    Dedicated CV Parsing engine that transforms extracted raw document text
    into structured candidate profiles using LLM reasoning (fail-fast, zero fallback).
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        if llm_provider:
            self.llm = llm_provider
        else:
            self.llm = get_llm_provider(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.DEFAULT_LLM_MODEL,
            )

    async def parse_cv_text(self, raw_text: str, filename: str = "") -> Dict[str, Any]:
        """
        Parse raw resume text into structured JSON data.
        Uses LLM parsing and strictly fails fast if input is empty, LLM is down, or response is invalid.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError(f"Cannot parse empty resume text for file: {filename or 'unknown'}")

        prompt = f"Resume Document: {filename}\n\nRaw Resume Text:\n{raw_text[:4000]}"
        try:
            response = await self.llm.generate_response(
                system_prompt=CV_PARSER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                temperature=0.1,
            )
            data = json.loads(response)
        except Exception as exc:
            logger.error("LLM CV parser failed for %s: %s", filename, exc)
            raise RuntimeError(f"LLM CV parser failed for file {filename}: {exc}") from exc

        if not isinstance(data, dict) or not data.get("name"):
            raise RuntimeError(
                f"LLM CV parser returned invalid structure for file {filename}: expected JSON object with 'name'"
            )

        return data


cv_parser = CVParser()
