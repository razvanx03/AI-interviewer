import json
import re
import logging
from typing import Dict, Any, Optional
from llm import get_llm_provider, BaseLLMProvider
from core.config import settings
from core.constants import TECH_CATALOGUE

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
    into structured candidate profiles using LLM reasoning (with heuristic fallback).
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
        Attempts LLM parsing first, with heuristic regex fallback.
        """
        if not raw_text or not raw_text.strip():
            return self._heuristic_fallback(raw_text, filename)

        try:
            prompt = f"Resume Document: {filename}\n\nRaw Resume Text:\n{raw_text[:4000]}"
            response = await self.llm.generate_response(
                system_prompt=CV_PARSER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                temperature=0.1,
            )
            data = json.loads(response)
            if isinstance(data, dict) and data.get("name"):
                return data
            logger.warning("LLM CV parser returned unexpected structure, applying heuristic fallback.")
            return self._heuristic_fallback(raw_text, filename, partial_data=data if isinstance(data, dict) else None)
        except Exception as exc:
            logger.warning("LLM CV parser failed (%s), falling back to heuristic parsing.", exc)
            return self._heuristic_fallback(raw_text, filename)

    def _heuristic_fallback(
        self, raw_text: str, filename: str = "", partial_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deterministic heuristic extraction if LLM is unavailable."""
        data = partial_data or {}
        text = raw_text or ""

        # Extract name from filename or first non-empty line
        if not data.get("name") or data.get("name") == "Candidate Full Name":
            clean_name = re.sub(r'(\.pdf|\.docx|\.doc|_resume|_cv|[-_])', ' ', filename, flags=re.IGNORECASE).strip()
            if clean_name and len(clean_name) > 2:
                data["name"] = clean_name.title()
            else:
                first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Candidate")
                data["name"] = first_line[:50] if len(first_line) < 50 else "Candidate"

        # Extract Email
        if not data.get("email"):
            email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
            data["email"] = email_match.group(0) if email_match else None

        # Extract Phone
        if not data.get("phone"):
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            data["phone"] = phone_match.group(0) if phone_match else None

        # Extract Skills from tech catalogue
        if not data.get("skills"):
            text_lower = text.lower()
            data["skills"] = [t for t in TECH_CATALOGUE if t.lower() in text_lower]

        # Extract Experience Years estimate
        if not data.get("experience_years"):
            exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience', text, re.IGNORECASE)
            data["experience_years"] = int(exp_match.group(1)) if exp_match else 3

        if not data.get("summary"):
            skills_str = ", ".join(data.get("skills", [])[:4]) if data.get("skills") else "software engineering"
            data["summary"] = f"Candidate with background in {skills_str} and relevant software engineering experience."

        if not data.get("education"):
            data["education"] = []
        if not data.get("work_history"):
            data["work_history"] = []

        return data

cv_parser = CVParser()
