# AI-Powered Job Interviewer

An autonomous, privacy-first technical job interviewer platform that conducts live, adaptive screening interviews tailored to specific job descriptions and candidate resumes.

[![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite%20%2B%20shadcn%2Fui-blue)](app/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLAlchemy%202.0-emerald)](api/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016%20%2B%20pgvector-indigo)](docker-compose.yml)
[![Container](https://img.shields.io/badge/Docker-3--Container%20Orchestration-cyan)](docs/docker.md)
[![Animations](https://img.shields.io/badge/Animations-Thinking%20Orbs-violet)](https://github.com/Jakubantalik/thinking-orbs)

---

## 🏛️ System Architecture

```
AI-interviewer/
├── app/                      # React 19 + TypeScript + Vite + Tailwind CSS + shadcn/ui
├── api/                      # FastAPI Python backend (SQLAlchemy 2.0 Async + asyncpg)
├── llm/                      # Standalone LLM Provider layer (Mock, Ollama, Prompt Engineering)
├── docs/                     # Mirrored technical documentation
│   ├── ARCHITECTURE.md       # Full system design and data-flow map
│   ├── docker.md             # Docker multi-container guide
│   ├── app/                  # Frontend pages, components, and state docs
│   ├── api/                  # Backend endpoints, schemas, and service docs
│   └── llm/                  # AI engine, prompts, and vector integration docs
├── docker-compose.yml        # 3-Service environment (app, api, postgres)
├── AGENTS.md                 # Mandatory instructions for AI agents and developers
└── README.md
```

For comprehensive technical specifications, refer to [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## ✨ Key Features

- **Autonomous Goal-Oriented AI Interviewer**: Conducts live, interactive technical interviews driven by a multi-competency assessment checklist. Qwen autonomously decides when sufficient evidence has been gathered to conclude the interview and generate the evaluation report.
- **Human-Like Dialogue & Clarification Loops**: Candidates can ask technical clarification and counter-questions at any point. The AI answers queries concisely, retains the active interview question state in PostgreSQL, and smoothly steers the candidate back to the problem without skipping topics.
- **Deterministic State Machine & Failsafe Guards**: PostgreSQL tracks `active_question_number` and consecutive clarifications while maintaining configurable failsafe limits (`SAFETY_MAX_QUESTIONS`) against infinite conversational loops.
- **ChatGPT/Claude Styled Interface**: Sleek dark/light theme, collapsible navigation rail, search filter, and custom modal dialogs.
- **Thinking Orbs Animations**: Native 2D canvas visual state indicators (`connecting`, `solving`) powered by [`thinking-orbs`](https://github.com/Jakubantalik/thinking-orbs).
- **Real-Time Token Streaming**: Server-Sent Events (SSE) streaming pipeline delivering instantaneous AI token rendering.
- **Persistent PostgreSQL Storage**: Asynchronous session and transcript storage with SQLAlchemy 2.0 and `asyncpg` with cascading cleanups.
- **Mobile-First Responsive UX**: Mobile drawer with swipe-to-delete gestures, interactive slide arrows, and dynamic header wrapping.
- **Internationalization (i18n)**: Instant runtime language switching between English (🇬🇧) and Romanian (🇷🇴).
- **Privacy & Local AI Ready**: Decoupled architecture serving local Ollama models (Qwen, Llama 3, DeepSeek) with direct CUDA acceleration and PostgreSQL + pgvector embeddings.

---

## 🚀 Quick Start

### Option 1: Complete 3-Container Docker Setup (Recommended)

Run the entire stack (React frontend, FastAPI backend, and PostgreSQL with pgvector) with a single command:

```bash
docker compose up -d --build
```

- 🌐 **Frontend SPA**: [http://localhost:5173](http://localhost:5173)
- ⚙️ **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🗄️ **PostgreSQL Database**: `localhost:5432` (`user: postgres`, `password: postgres`, `db: ai_interviewer`)

To inspect logs:
```bash
docker compose logs -f
```

For full container documentation, see [`docs/docker.md`](docs/docker.md).

---

### Option 2: Local Development

#### 1. Database (PostgreSQL)
Ensure a PostgreSQL instance is running on `localhost:5432` with database `ai_interviewer`. Configure credentials in the root `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_interviewer
```

#### 2. Backend (`api/`)
```bash
cd api
python main.py
```
*(Automatically bootstraps the local virtual environment and launches on [http://localhost:8000](http://localhost:8000)).*

#### 3. Frontend (`app/`)
```bash
cd app
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🛠️ Code Quality & Contribution Rules

Before submitting pull requests or completing AI agent tasks:
- Ensure ESLint passes with **0 errors**: `npm run lint` inside `app/`.
- Ensure Prettier formatting is compliant: `npm run format:check`.
- Verify production build compiles cleanly: `npm run build`.
- Keep technical specifications in `docs/` and Docker configurations in sync as mandated in [`AGENTS.md`](AGENTS.md).
