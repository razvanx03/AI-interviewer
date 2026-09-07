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
  - **Robust Q&A Transcript Mapping in Evaluation Reports**: When formatting evaluated strengths and weaknesses into structured Markdown tables, `_format_eval_feedback_section` integrates `qa_rounds_map` derived from `parse_transcript_into_qa_rounds`. If the LLM omits candidate response text or question summaries in its output (e.g. for strengths), the service dynamically resolves the candidate's actual transcript answer and question text, preventing false `(Fără răspuns)` / `(No response provided)` indicators on answered questions.
  - **Deterministic Session Coverage Governance**: When an interview session terminates prematurely (e.g. candidate answers 2 questions out of 9 planned competencies), `_generate_evaluation_closing` deterministically calculates `coverage_ratio = answered_count / total_planned_topics` and scales `overall_score = round(raw_score * coverage_ratio, 1)`. If coverage is below 50%, recommendation is strictly downgraded to `No Hire` (or `Leaning No Hire` if below 70%). All unassessed planned competencies are automatically appended to the gaps table with `(Neevaluat - Sesiune finalizată prematur)` / `(Unassessed - Session Concluded Early)` badges, preventing unearned passing scores.

## 2. `screening_service.py`
- **Class**: `ScreeningService`
- **Responsibilities**:
  - Multi-candidate semantic screening via RAG and pgvector cosine similarity search.
  - Generates semantic embeddings for candidate CV chunks using `nomic-embed-text` with fail-fast validation.
  - Dynamic domain classification (`_detect_candidate_domain`) and domain alignment compatibility (`_compute_domain_compatibility`).
  - Strict domain score ceilings protecting against keyword-stuffing / buzzwords across engineering disciplines (`WEB_BACKEND`, `FULL_STACK`, `DATA_ENGINEERING`, `EMBEDDED_AUTOMOTIVE`, `INDUSTRIAL_HARDWARE`, `QA_TESTING`, `NON_IT`, `BLANK_OR_TEMPLATE`).
  - **Deterministic Tie-Breaking**: When candidates achieve identical `match_score` values (e.g. 97%), `results.sort` prioritizes the candidate with the highest verified `experience_years` (`key=lambda x: (x.get("match_score", 0), x.get("experience_years", 0.0)), reverse=True`).
  - Sets `is_selected = True` on the #1 ranked candidate unless explicitly overridden by a recruiter selection (`selected_candidate_name`).

## 3. `cv_parser.py`
- **Class**: `CVParser`
- **Responsibilities**:
  - Structured CV data parsing via LLM with strict fail-fast validation (zero mock/heuristic fallbacks).
  - In-memory document processing for dynamic candidate profiling.

## 4. `llm/`
- **Classes**: `BaseLLMProvider`, `OllamaProvider`
- Provides asynchronous token streaming (`POST /api/chat`) and structured generation.
