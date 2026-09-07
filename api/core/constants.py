"""
Centralized constants for the API and business logic layer.
"""
from typing import List, Optional
import re
import unicodedata

# Predefined Technology Knowledge Base for Resume Keyword Matching
TECH_CATALOGUE: List[str] = [
    ".NET",
    "C#",
    "React",
    "TypeScript",
    "JavaScript",
    "Python",
    "FastAPI",
    "Django",
    "Node.js",
    "PostgreSQL",
    "MySQL",
    "MariaDB",
    "MongoDB",
    "Redis",
    "SQL Server",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "Azure DevOps",
    "GCP",
    "GraphQL",
    "REST",
    "CI/CD",
    "Tailwind",
    "Next.js",
    "Vue",
    "Angular",
    "Java",
    "Spring Boot",
    "Go",
    "Rust",
    "Git",
    "Ruby",
    "Rails",
    "Ruby on Rails",
]

# Interview Pacing & Adaptive State Machine Limits
CLARIFICATION_STEER_THRESHOLD: int = 3
INTERVIEW_COMPLETE_TOKEN: str = "[INTERVIEW_COMPLETE]"

# Screening Algorithm Weights & Thresholds
BASE_SCREENING_SCORE: int = 65
KEYWORD_MATCH_WEIGHT: int = 5
MAX_KEYWORD_BOOST: int = 25
STRENGTH_MATCH_WEIGHT: int = 4
MAX_STRENGTHS_BOOST: int = 20
MAX_SCREENING_SCORE: int = 98

def sanitize_postgres_text(text: Optional[str]) -> str:
    """
    Sanitize text strings for PostgreSQL storage:
    - Removes 0x00 null bytes (CharacterNotInRepertoireError).
    - Removes non-printable ASCII control characters (preserving newline, return, tab).
    - Normalizes Unicode to standard NFC form.
    """
    if not text:
        return ""
    cleaned = str(text).replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", cleaned)
    try:
        cleaned = unicodedata.normalize("NFC", cleaned)
    except Exception:
        pass
    return cleaned.strip()
