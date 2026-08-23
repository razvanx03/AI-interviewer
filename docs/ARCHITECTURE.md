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
  - `/` -> `HomePage` (New Interview Configuration Wizard & Multi-Candidate Pool)
  - `/interview/:id` -> `InterviewRoomPage` (Real-time AI Chat stream & Transcript)
  - `*` -> `NotFoundPage` (404 Screen)
- **Layout**: `AppLayout` rendering persistent `Sidebar` and dynamic `Outlet`.
- **UI Components**: Strict shadcn/ui components (`Button`, `Card`, `Dialog`, `Input`, `Textarea`, `Badge`, `Select`, `Separator`).
- **Screening & Wizard**: 3-Step Setup Wizard (Role Details -> Multi-CV Candidate Pool -> AI Winner Selection & Candidate Invite Link).
- **Styling**: Tailwind CSS with Zinc/Neutral dark palette (`#09090b`).
- **Internationalization (i18n)**: English (🇬🇧) and Romanian (🇷🇴) dictionary managed via `LanguageProvider` & `useLanguage()`.
- **State & Context**: `InterviewProvider` & `useInterviews()` hook syncing PostgreSQL transcripts and `localStorage` cache.

### Backend Architecture (`api/`)

- **FastAPI**: Asynchronous Python backend with SQLAlchemy 2.0 AsyncSession.
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
- **Deterministic Topic Transitions**:
  - Each topic is capped at a maximum of 1 follow-up turn.
  - If the candidate answers or requests to pass (*"nu stiu", "sa continuam", "skip"*), the backend state machine automatically advances `current_topic_index += 1`, resets the follow-up counter, and gives the LLM the next topic.
  - When all topics in the plan are covered, the interview concludes autonomously and generates the candidate evaluation report.
- **Zero-Repetition & Anti-Echo Protocol**: The LLM prompt is strictly instructed to evaluate only the candidate's latest turn, with explicit anti-echo mandates preventing verbatim repetition of previous interviewer questions.

### LLM Module (`llm/`)

- Standalone AI provider abstractions (`BaseLLMProvider`).
- `OllamaProvider`: Native asynchronous HTTP client for local model serving with sampling parameters (`repeat_penalty: 1.18`, `presence_penalty: 0.6`, `frequency_penalty: 0.5`, `top_p: 0.9`).
- `INTERVIEWER_SYSTEM_PROMPT`: Structured prompt builder injecting dynamic topic focus, few-shot turn examples, and strict language mirroring.
  - **Assessment Checklist**: Multi-dimensional competencies (Core Technology, Architecture & Scalability, Database Modeling, CV Claims, Edge Cases) evaluated before concluding.
  - **Intent Classification & Re-steering**: Differentiates candidate answers (`[ANSWER]`) from counter-questions / clarifications (`[QUESTION]`). Clarifications are answered concisely while steering the candidate back to the active problem without losing context.
  - **Autonomous Completion Protocol**: AI emits `[INTERVIEW_COMPLETE]` once checklist evidence is sufficient.
- **Deterministic State Tracking**: PostgreSQL persists `active_question_number` and `consecutive_clarifications`. Soft prompt steering is injected if clarifications exceed `CLARIFICATION_STEER_THRESHOLD` (3), with `SAFETY_MAX_QUESTIONS` (15) acting strictly as an abnormal loop failsafe.

### Documentation & Docker

- **`docs/`**: Mirrored documentation tree reflecting each component and folder in the application.
- **`docker-compose.yml`**: 3-container microservices environment (`frontend`, `backend`, `db`). See [`docs/docker.md`](file:///c:/Users/ander/Desktop/AI%20interviewer/docs/docker.md).
