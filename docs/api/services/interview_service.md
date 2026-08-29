# Services (`api/services/`)

## 1. `interview_service.py`
- **Class**: `InterviewService`
- **Responsibilities**:
  - PostgreSQL session management via SQLAlchemy 2.0 `AsyncSession`.
  - Dynamic topic state machine extracted from Job Description.
  - Multi-CV candidate screening and scoring (`screen_candidates`).
  - **Smart Name Extraction Fallback**: If a candidate's name is the default fallback `"Candidate"` (e.g. from `CV.pdf`), extracts the candidate's real full name from the document header while strictly preserving any custom or pre-set candidate names.
  - Conversational message streaming via SSE (`/stream`).
  - Comprehensive candidate evaluation generation upon completion.

## 2. `cv_service.py` & `cv_parser.py`
- **Class**: `CVService` & `CVParser`
- **Responsibilities**:
  - File storage in `storage/cvs/` and metadata persistence in `cvs` table.
  - Document text extraction and structured parsing via LLM / heuristic fallback.

## 3. `llm/`
- **Classes**: `BaseLLMProvider`, `OllamaProvider`
- Provides asynchronous token streaming (`POST /api/chat`) and structured generation.
