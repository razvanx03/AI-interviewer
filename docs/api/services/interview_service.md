# Services (`api/services/`)

## 1. `interview_service.py`
- **Class**: `InterviewService`
- **Responsibilities**:
  - In-memory session store `_sessions: Dict[str, InterviewSession]`.
  - Session creation with tailored initial question.
  - Message state appending and conversation orchestration.
  - Ready for drop-in migration to PostgreSQL SQLAlchemy async repository.

## 2. `cv_service.py`
- **Class**: `CVService`
- **Responsibilities**:
  - `parse_cv_file(filename, file_bytes, content_type)`
  - Formats raw resume text and extracts candidate competencies.
  - Ready to wire `pymupdf` (PDF) and `python-docx` (DOCX).

## 3. `llm/`
- **Classes**: `BaseLLMProvider`, `MockLLMProvider`
- Provides standard contract for generating responses and token streams.
