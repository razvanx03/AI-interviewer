# System Architecture

## 1. System Overview

The **AI-Powered Job Interviewer** is a modern, privacy-centric platform designed with an **AI Chat Interface** (ChatGPT / Claude layout) and a decoupled PostgreSQL backend.

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
                         HTTP / REST | WebSocket Streaming
                                     v
+-------------------------------------------------------------------------+
|                               api/ (FastAPI)                            |
|  - Asynchronous Endpoints (/api/v1/interviews, /chat, /cv)              |
|  - SQLAlchemy 2.0 Async Session Management                              |
|  - Database Models: interviews & messages tables                        |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         PostgreSQL Database (pgvector)                  |
|  - Table: `interviews` (UUID, job title, company, enums, timestamps)    |
|  - Table: `candidates` (UUID, interview_id FK, name, CV, score, status)|
|  - Table: `messages` (UUID, interview_id FK, role ENUM, content, q_num) |
|  - Native Enums: `experience_level_enum`, `interview_status_enum`, etc. |
|  - Schema Migrations managed strictly via Alembic                       |
+-------------------------------------------------------------------------+
```

---

## 2. Directory Separation & Responsibility

## Frontend Architecture (`app/`)

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

- **`api/`**: Asynchronous Python backend powered by FastAPI, SQLAlchemy 2.0 with PostgreSQL persistence, automated multi-candidate scoring, and version-controlled schema migrations via **Alembic** (`alembic/versions/`).
- **`llm/`**: Standalone AI & Prompt Engineering layer with `BaseLLMProvider` abstractions.
- **`docs/`**: Mirrored documentation tree reflecting each component and folder in the application.
- **`docker-compose.yml`**: 3-container microservices environment (`frontend`, `backend`, `db`). See [`docs/docker.md`](file:///c:/Users/ander/Desktop/AI%20interviewer/docs/docker.md).
