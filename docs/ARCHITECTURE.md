# System Architecture

## 1. System Overview

The **AI-Powered Job Interviewer** is a modern, privacy-centric platform designed with an **AI Chat Interface** (ChatGPT / Claude layout) and a decoupled PostgreSQL backend with local LLM serving.

```
+-------------------------------------------------------------------------+
|                              Browser (React 19)                         |
|  +---------------------------+---------------------------------------+  |
|  |       Left Sidebar        |         Center Main Workspace         |  |
|  | - "+ New Interview" Button| - Interview Setup Form (if new)       |  |
|  | - Chat & Interview History| - Sticky Header with Role Info        |  |
|  | - LocalStorage IDs Cache  | - Centered Message Timeline (AI/User) |  |
|  | - Theme Toggle Switcher   | - Docked Bottom Chat Input Bar        |  |
|  +---------------------------+---------------------------------------+  |
+------------------------------------+------------------------------------+
                                     |
                         HTTP / REST | SSE Token Streaming
                                     v
+-------------------------------------------------------------------------+
|                               api/ (FastAPI)                            |
|  - Asynchronous Endpoints (/api/v1/interviews, /chat, /stream, /cv)     |
|  - SQLAlchemy 2.0 Async Session Management                              |
|  - Database Models: interviews, candidates, and messages tables         |
+------------------------------------+------------------------------------+
                                     |
               +---------------------+---------------------+
               |                                           |
               v                                           v
+-----------------------------+             +-----------------------------+
|    PostgreSQL Database      |             |     llm/ (Ollama / Local)   |
| - interviews table          |             | - OllamaProvider (Async HTTP|
| - candidates table          |             | - Model: qwen3-cs / qwen2.5 |
| - messages table            |             | - Streaming /api/chat (SSE) |
| - Alembic Schema Migrations |             | - Dynamic Prompt Engine     |
+-----------------------------+             +-----------------------------+
```

---

## 2. Directory Separation & Responsibility

### Frontend Architecture (`app/`)

- **Framework**: React 18 + Vite + TypeScript.
- **Routing**: `react-router-dom` declarative page routes:
  - `/login` -> `LoginPage` (Admin Recruiter JWT Authentication)
  - `/` -> `HomePage` (Protected Admin Dashboard, New Interview Wizard & Multi-Candidate Pool)
  - `/interview/:id` -> `InterviewRoomPage` (Role-aware AI Chat stream, Transcript, & Dual Evaluation View)
  - `*` -> `NotFoundPage` (404 Screen)
- **Layout**: `AppLayout` rendering persistent role-aware `Sidebar` and dynamic `Outlet`.
- **UI Components**: Strict shadcn/ui components (`Button`, `Card`, `Dialog`, `Input`, `Textarea`, `Badge`, `Select`, `Separator`).
- **Screening & Wizard**: 3-Step Setup Wizard (Role Details -> Multi-CV Candidate Pool -> Winner Selection & Invitation Link Generation).
- **Styling**: Tailwind CSS with Zinc/Neutral dark palette (`#09090b`).
- **Internationalization (i18n)**: English (🇬🇧) and Romanian (🇷🇴) dictionary managed via `LanguageProvider` & `useLanguage()`.
- **State & Context**: `InterviewProvider`, `AdminAuthProvider` (`useAdminAuth()`), and `useInterviews()` hook syncing PostgreSQL transcripts and JWT auth state.

### Backend Architecture (`api/`)

- **FastAPI**: Asynchronous Python backend with SQLAlchemy 2.0 AsyncSession.
- **Authentication & Security**:
  - `users` table with bcrypt password hashes.
  - JWT Bearer Token generation (`HS256`).
  - Route protection dependencies: `get_current_user`, `get_current_admin`.
  - Open public candidate endpoints for interview rooms.
- **Endpoints**:
  - `POST /api/v1/interviews`: Creates interview and generates personalized AI opening question.
  - `POST /api/v1/interviews/{id}/stream`: Real-time token streaming via Server-Sent Events (SSE).
  - `POST /api/v1/interviews/{id}/complete`: Finalizes interview and triggers AI Evaluation Report.
  - `POST /api/v1/cv/extract-batch`: In-memory multi-document text extraction (PDF/DOCX) returning sanitized text items.
  - `POST /api/v1/interviews/screen`: Multi-candidate semantic screening via RAG and pgvector similarity search.
- **RAG & Vector Screening Architecture**:
  - `SemanticTextSplitter`: Recursive character text splitting (500 chars, 50 overlap) respecting semantic boundaries.
  - `TimelineExtractor`: Section-aware tenure calculator isolating verified employment from university/high school education, student clubs, and courses.
  - `OllamaProvider.embed_documents` / `embed_text`: Generates 768-dim vector embeddings using `nomic-embed-text`.
  - `pgvector`: PostgreSQL vector extension storing chunks in `cv_chunks` with `candidate_id` foreign key index and HNSW cosine similarity index.
  - `ScreeningService`: Multi-PDF semantic ingestion, unique candidate ID isolation, domain relevancy classification (`_classify_candidate_domain`), domain score ceilings (`WEB_BACKEND`, `DATA_ENGINEERING`, `EMBEDDED_AUTOMOTIVE`, `INDUSTRIAL_PLC`, `NON_IT`, `BLANK_FORM`), and comparative RAG synthesis.
- **Document Processing**:
  - `DocumentExtractor`: In-memory PDF (`pypdf` + `pypdfium2` OCR) and DOCX (`python-docx` + embedded images OCR) extraction.
  - `CVParser`: Transforms raw text into structured JSON via Qwen LLM with strict fail-fast validation (zero mock/heuristic fallbacks).
- **Test Suite & Verification Architecture (`api/tests/`)**:
  - Automated unit and integration tests (100% green) covering all critical components:
    - `test_document_extractor.py`: PDF/DOCX magic bytes validation, paragraph/table extraction, and error handling.
    - `test_cv_parser.py`: LLM structured parsing and strict fail-fast error assertions.
    - `test_ocr_service.py`: In-memory OCR, image conversion, and exception resilience.
    - `test_ollama_provider.py`: Payload construction, streaming, JSON repair, and strict fail-fast embedding errors.
    - `test_constants_and_sanitizer.py`: UTF-8/NFC sanitization, null byte removal, and constants invariants.
    - `test_screening_service.py`: pgvector cosine search, timeline extraction, and candidate tenure weighting.
    - `test_interview_service.py`: Dynamic opening, answer progression, and clarification state machine.
    - `test_intent_classifier.py`: Clarification, refusal, profanity, and language detection.
    - `test_prompts.py`: Seniority rubrics and bilingual prompt templates.
    - `test_auth_service.py`: Password hashing, JWT creation, and expiry.
    - `test_api_endpoints.py`: Integration testing of all REST and SSE endpoints.
- **Migrations**: Version-controlled PostgreSQL migrations managed strictly via **Alembic** (`alembic/versions/`).

### LangGraph Conversational Interview Workflow (`llm/agent/`)

The multi-turn conversational interview lifecycle is fully orchestrated via a compiled **LangGraph `StateGraph`** (`llm/agent/graph.py`), replacing ad-hoc monolithic branching with modular, testable graph nodes:

```
[START]
   │
   ▼
[process_candidate_response] (Router Node)
   ├── intent: GREETING ──────────────► [start_interview] ──► [END]
   ├── intent: CLARIFICATION ─────────► [detect_clarification] ──► [END]
   ├── intent: LANGUAGE_SWITCH ───────► [language_switch] ──► [END]
   ├── intent: PROFANE / OFF_TOPIC ───► [guardrail] ──► [END]
   ├── intent: REFUSAL ───────────────► [detect_refusal]
   │                                         ├── completed ────► [generate_final_evaluation] ──► [END]
   │                                         └── active ───────► [END]
   ├── intent: WRAP_UP ───────────────► [generate_final_evaluation] ──► [END]
   └── intent: ANSWER ────────────────► [evaluate_answer]
                                             ├── is_complete ──► [generate_final_evaluation] ──► [END]
                                             ├── needs_follow_up ► [generate_follow_up] ────────► [END]
                                             └── next_topic ───► [move_to_next_question] ──────► [END]
```

- **Graph State (`InterviewState`)**: Declared with `TypedDict` in `llm/agent/state.py` containing session metadata, active topic index, assessed topics, clarification counters, follow-up flags, and candidate message.
- **Graph Nodes (`llm/agent/nodes.py`)**:
  - `start_interview_node`: Greets candidate and generates first question on Topic 1.
  - `process_candidate_response_node`: Classifies candidate intent (`ANSWER`, `CLARIFICATION`, `REFUSAL`, `LANGUAGE_SWITCH`, `WRAP_UP`, `PROFANE_LANGUAGE`, `OFF_TOPIC`).
  - `detect_clarification_node`: Responds to clarifying questions concisely and redirects to active question.
  - `detect_refusal_node`: Empathetically handles skip / "don't know", advances topic index, and formulates next prompt.
  - `evaluate_answer_node`: Evaluates technical response, triggers follow-up for shallow answers, and monitors completion.
  - `generate_follow_up_node`: Probes candidate's previous response deeper on the same topic.
  - `move_to_next_question_node`: Formulates the technical question for the next planned competency.
  - `language_switch_node`: Dynamically translates active prompt between Romanian and English.
  - `generate_final_evaluation_node`: Concludes interview, appends `[INTERVIEW_COMPLETE]`, and triggers report generation.
  - `guardrail_node`: Firmly and calmly steers inappropriate or off-topic messages back to the interview.

### LLM Module (`llm/`)

- Standalone AI provider abstractions (`BaseLLMProvider`).
- `OllamaProvider`: Native asynchronous HTTP client for local Qwen 3.5 8B model serving with sampling parameters and streaming SSE support.
- **LangChain Integration**:
  - `langchain-text-splitters`: `RecursiveCharacterTextSplitter` in `llm/chunking.py`.
  - `langchain-ollama`: `OllamaEmbeddings` for query and document vectors.
  - `langchain-core`: `JsonOutputParser` and standardized `Document` metadata extraction.
- **LangGraph Integration**: Full conversational state graph in `llm/agent/`.
- Modular, focused prompt templates in `llm/prompts.py` avoiding bloated system prompts.
- **Fair Evaluation Principles**: Evaluator strictly differentiates clarifications and language switches from knowledge gaps, scoring only demonstrated technical proficiency.

### Automated Test Suite (`api/tests/`)

- **Pytest Asyncio Test Suite**: 101 automated unit tests passing with 100% green:
  - `test_interview_graph.py`: Comprehensive test suite verifying all 8 LangGraph state machine pathways.
  - `test_interview_service.py`: State machine transitions, clarification counters, language switching, and lifecycle management.
  - `test_screening_service.py`: pgvector cosine search, LangChain embeddings, timeline extraction, and candidate tenure weighting.
  - `test_document_extractor.py`: PDF/DOCX magic bytes validation, LangChain Document wrapping, and error handling.
  - `test_prompts.py`: Seniority rubrics, Romanian 2nd person singular tone, direct question generation, and evaluations.
  - `test_intent_classifier.py`: Exact intent classification, candidate name sanitizer, and response cleaner.
  - `test_auth_service.py`: Bcrypt password hashing, JWT encoding/decoding, and expiration.
  - `test_cv_parser.py`: LLM structured parsing and strict fail-fast error assertions.

### Documentation & Docker

- **`docs/`**: Mirrored documentation tree reflecting each component and folder in the application.
- **`docker-compose.yml`**: 3-container microservices environment (`frontend`, `backend`, `db`). See [`docs/docker.md`](file:///c:/Users/ander/Desktop/AI%20interviewer/docs/docker.md).
