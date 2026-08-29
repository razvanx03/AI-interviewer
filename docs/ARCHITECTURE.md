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
  - `POST /api/v1/cv/upload`: Validates magic bytes, extracts text in-memory with PaddleOCR fallback, parses structured CV data, stores original file, and records in PostgreSQL.
  - `GET /api/v1/cv/{id}/download`: Downloads original PDF/DOCX document from storage.
  - `DELETE /api/v1/interviews/admin/clear-all`: Developer utility to wipe state.
- **Document Processing & Storage**:
  - `DocumentExtractor`: In-memory PDF (`pypdf` + `pypdfium2` OCR) and DOCX (`python-docx` + embedded images OCR) extraction.
  - `CVParser`: Transforms raw text into structured JSON via Qwen LLM.
  - `CVService`: Filesystem storage (`storage/cvs/`) + PostgreSQL `cvs` metadata table.
- **Migrations**: Version-controlled PostgreSQL migrations managed strictly via **Alembic** (`alembic/versions/`).

### Dynamic Topic State Machine & Pacing

- **Dynamic Job Description Extraction**: Upon session creation, the backend extracts 4 to 6 core technical pillars directly from the Job Description (e.g., `["React 19 & TypeScript", "Python FastAPI", "PostgreSQL Optimization", "Docker & CI/CD"]`).
- **Direct, Natural Opening Turn**:
  - Greet candidate warmly in 1 natural sentence (with username sanitization, e.g. `Dariusbotezan2026` $\rightarrow$ `Darius`).
  - Immediately pose **Question 1** on the first technical pillar extracted from the Job Description at the chosen seniority level (`MID`).
  - Eliminates awkward robotic meta-intro dialogues (*"V-aș ruga să mă accepti..."* / *"Sesionul va dura..."*).
- **Deterministic Intent Classification & Safety Bounds**:
  - `CLARIFICATION`: Explains requested concept concisely (1-2 sentences) and repeats `active_question_text`. The active question is **NOT marked answered**.
  - Consecutive clarifications are bounded by safety threshold (`CLARIFICATION_STEER_THRESHOLD = 3`).
  - `REFUSAL_OR_DONT_KNOW`: Acknowledges supportively in 1 sentence and rotates to the next competency.
  - `LANGUAGE_REQUEST`: Switches language dynamically (`ro` / `en`) and translates active question without penalty.
  - `ANSWER`: Acknowledges candidate's answer, marks competency in `assessed_topics`, and moves to next question.
- **Context Window Management & Progressive Summarization**:
  - Token threshold monitoring (`CONTEXT_TOKEN_THRESHOLD_RATIO = 0.60`).
  - Rolling window of recent messages (`RECENT_MESSAGES_WINDOW_COUNT = 6`).
  - Progressive cumulative summary stored in PostgreSQL (`interviews.conversation_summary`).
  - Map-Reduce chunked evaluation (`evaluate_interview`) for long transcripts.

### LLM Module (`llm/`)

- Standalone AI provider abstractions (`BaseLLMProvider`).
- `OllamaProvider`: Native asynchronous HTTP client for local Qwen 3.5 8B model serving with sampling parameters and streaming SSE support.
- Modular, focused prompt templates in `llm/prompts.py` avoiding bloated system prompts.
- **Fair Evaluation Principles**: Evaluator strictly differentiates clarifications and language switches from knowledge gaps, scoring only demonstrated technical proficiency.

### Automated Test Suite (`api/tests/`)

- **Pytest Asyncio Test Suite**: 49 automated unit and integration tests executed in <5s without external Ollama dependencies.
- **Unit Tests (`api/tests/unit/`)**:
  - `test_prompts.py`: Seniority rubrics, Romanian 2nd person singular tone, direct question 1 generation, clarifications, skips, and evaluation aggregation.
  - `test_intent_classifier.py`: Exact intent classification (`READY`, `CLARIFICATION`, `REFUSAL`, `LANGUAGE_REQUEST`, `ANSWER`), candidate name sanitizer, and response cleaner.
  - `test_interview_service.py`: State machine transitions, clarification counters, language switching, and lifecycle management.
  - `test_auth_service.py`: Bcrypt password hashing, JWT encoding/decoding, and expiration.
  - `test_cv_service.py`: Magic bytes validation, in-memory PDF/DOCX parsing, and heuristic extraction fallback.
- **Integration Tests (`api/tests/integration/`)**:
  - `test_api_endpoints.py`: End-to-end testing of `/api/v1/auth/*`, `/api/v1/interviews/*` (chat, streaming SSE, screening, lifecycle), and error boundaries.

### Documentation & Docker

- **`docs/`**: Mirrored documentation tree reflecting each component and folder in the application.
- **`docker-compose.yml`**: 3-container microservices environment (`frontend`, `backend`, `db`). See [`docs/docker.md`](file:///c:/Users/ander/Desktop/AI%20interviewer/docs/docker.md).
