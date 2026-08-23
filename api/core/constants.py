"""
Centralized constants for the API and business logic layer.
"""
from typing import List

# Predefined Technology Knowledge Base for Resume Keyword Matching
TECH_CATALOGUE: List[str] = [
    "React",
    "TypeScript",
    "JavaScript",
    "Python",
    "FastAPI",
    "Django",
    "Node.js",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "GraphQL",
    "REST",
    "CI/CD",
    "Tailwind",
    "Next.js",
    "Java",
    "Go",
    "Rust",
]

# Interview Pacing & Adaptive State Machine Limits
CLARIFICATION_STEER_THRESHOLD: int = 3
INTERVIEW_COMPLETE_TOKEN: str = "[INTERVIEW_COMPLETE]"

# Screening Algorithm Weights & Thresholds
BASE_SCREENING_SCORE: int = 65
KEYWORD_MATCH_WEIGHT: int = 5
MAX_KEYWORD_BOOST: int = 25
STRENGTH_MATCH_WEIGHT: int = 3
MAX_STRENGTHS_BOOST: int = 10
MAX_SCREENING_SCORE: int = 99
