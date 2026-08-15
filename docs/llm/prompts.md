# Prompt Templates (`llm/prompts.py`)

## 1. `INTERVIEWER_SYSTEM_PROMPT`
- System prompt configuring the AI model to behave as an expert technical interviewer.
- Injects `job_title`, `job_description`, `candidate_cv`, and `experience_level`.
- Emphasizes evaluating tradeoffs, avoiding hallucination, and probing with follow-ups.

## 2. `CV_EXTRACTION_PROMPT`
- Structured extraction prompt asking the LLM to parse raw resume text into JSON (`skills`, `experience_years`, `summary`, `highlights`).
