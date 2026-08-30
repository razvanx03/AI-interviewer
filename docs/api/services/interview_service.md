# Services (`api/services/`)

## 1. `interview_service.py`
- **Class**: `InterviewService`
- **Responsibilities**:
  - PostgreSQL session management via SQLAlchemy 2.0 `AsyncSession`.
  - Dynamic topic state machine extracted from Job Description.
  - Multi-CV candidate screening and scoring (`screen_candidates`).
  - **Human Override Selection**: If the human user explicitly chooses a candidate in Step 3, their selection is honored with top priority (`selected_candidate_name`), overriding the AI's default #1 match score ranking.
  - **Output Sanitization & Anti-Roleplay**: `_clean_llm_response` automatically removes any `<think>` blocks, persona prefixes (e.g. `**You (...):**`, `Interviewer:`), and outer quotes from LLM outputs.
  - **Smart Name Extraction Fallback**: If a candidate's name is the default fallback `"Candidate"` (e.g. from `CV.pdf`), extracts the candidate's real full name from the document header while strictly preserving any custom or pre-set candidate names.
  - Conversational message streaming via SSE (`/stream`).
  - Comprehensive candidate evaluation generation upon completion with strict idempotency (updates existing wrap-up message or returns existing report, preventing duplicate closing messages across multiple finishes or page refreshes).
  - **Deterministic Hardcoded Closing**: The final thank-you message at interview conclusion is generated deterministically without calling the LLM, preventing candidate persona hallucination. The evaluator transcript strictly strips all wrapup messages to avoid penalizing candidates with fictitious unanswered final questions.

## 2. `cv_service.py` & `cv_parser.py`
- **Class**: `CVService` & `CVParser`
- **Responsibilities**:
  - File storage in `storage/cvs/` and metadata persistence in `cvs` table.
  - Document text extraction and structured parsing via LLM / heuristic fallback.

## 3. `llm/`
- **Classes**: `BaseLLMProvider`, `OllamaProvider`
- Provides asynchronous token streaming (`POST /api/chat`) and structured generation.
