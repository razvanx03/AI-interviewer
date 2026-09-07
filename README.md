# AI-Powered Job Interviewer

An autonomous, privacy-first technical job interviewer and candidate screening platform that conducts live, adaptive technical interviews and automated RAG-based resume screening tailored to custom job specifications.

[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%20%2B%20shadcn%2Fui-blue)](app/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLAlchemy%202.0-emerald)](api/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016%20%2B%20pgvector-indigo)](docker-compose.yml)
[![AI Engine](https://img.shields.io/badge/LLM-Fine--Tuned%20Qwen%20%2B%20Ollama-purple)](llm/)
[![Embeddings](https://img.shields.io/badge/Embeddings-nomic--embed--text-orange)](llm/)
[![Container](https://img.shields.io/badge/Docker-3--Container%20Stack-cyan)](docker-compose.yml)

---

## 🏛️ System Architecture

```
AI-interviewer/
├── app/                      # React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui
├── api/                      # FastAPI Python backend (SQLAlchemy 2.0 Async + asyncpg + Alembic)
├── llm/                      # Standalone LLM Provider layer (Ollama Provider, Prompt Engineering)
├── docs/                     # Mirrored technical documentation
│   ├── ARCHITECTURE.md       # High-level system design, data flow, and directory map
│   ├── docker.md             # Docker multi-container guide & networking
│   ├── app/                  # Frontend pages, components, hooks, and types
│   ├── api/                  # Backend endpoints, schemas, and service specs
│   └── llm/                  # AI engine, prompts, and pgvector RAG specs
├── docker-compose.yml        # 3-Service environment (frontend, backend, postgres+pgvector)
├── AGENTS.md                 # Developer & AI Agent instructions
└── README.md
```

For full technical specifications and data-flow diagrams, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## ✨ Key Features

### 1. Multi-CV Screening & RAG Ranking Engine
- **Multi-Document Ingestion**: Upload multiple candidate CVs simultaneously (`.pdf`, `.docx`, `.doc`, `.txt`) with automatic text and candidate name extraction.
- **pgvector Semantic Search**: Chunks resumes and computes vector embeddings using `nomic-embed-text` directly inside PostgreSQL via `pgvector` HNSW indexes.
- **Objective Candidate Ranking**: Measures semantic cosine similarity against custom Job Descriptions, verified employment tenure, and technical timelines to rank applicants with transparent match scores (0–100%), key strengths, and gap analyses.

### 2. Autonomous Technical Interviewer (LangGraph + Fine-Tuned Qwen)
- **Specialized Local AI Model**: Powered by a custom fine-tuned Qwen 8B model (`hf.co/radi04/qwen3-8b-cs-interviewer-merge-v1-150-q4:Q4_K_M`) designed specifically for technical computer science interviewing.
- **Adaptive Conversational Graph**: Orchestrated via LangGraph state machines with dynamic topic planning (defaults to 7 core technical topics for untimed interviews, dynamically scaled for timed sessions).
- **Intelligent Clarification Handling**: Distinguishes between candidate questions/clarifications and substantive answers, maintaining question state (`active_question_number`, `active_question_text`) without skipping topics or looping infinitely.
- **Autonomous Concluding & Evaluation**: Automatically wraps up when sufficient evidence is gathered across all competencies, generating a detailed multi-metric evaluation report (Technical Depth, Problem Solving, Communication, Experience) with hiring recommendations.

### 3. Enterprise Security & State Persistence
- **JWT Authentication**: Secure recruiter authentication with bcrypt password hashing and automatic admin account initialization on startup.
- **Zero Silent Fallbacks**: Strict fail-fast architecture — no fake embeddings, no mocked responses, and no masked errors in production.
- **Relational PostgreSQL Persistence**: Complete session state, candidate pool, question tracking, and chat transcripts stored via SQLAlchemy 2.0 and `asyncpg`.

### 4. Modern User Experience
- **ChatGPT/Claude-Style Chat UI**: Clean dark/light theme built with shadcn/ui components and accessible Radix UI primitives.
- **Real-Time Token Streaming**: Server-Sent Events (SSE) deliver low-latency token-by-token interviewer responses.
- **Thinking Orbs Animations**: Native 2D canvas visual state indicators (`connecting`, `thinking`, `speaking`) powered by [`thinking-orbs`](https://github.com/Jakubantalik/thinking-orbs).
- **Internationalization (i18n)**: Seamless runtime switching between English (🇬🇧) and Romanian (🇷🇴).

---

## 🚀 Quick Start (Docker Compose)

The recommended way to run the platform is using Docker Compose, which spins up the React frontend, FastAPI backend, and PostgreSQL with pgvector.

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Ollama](https://ollama.com/) running locally on your host machine with the required models:
  ```bash
  ollama pull nomic-embed-text
  ollama run hf.co/radi04/qwen3-8b-cs-interviewer-merge-v1-150-q4:Q4_K_M
  ```

### 2. Environment Configuration
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```
Ensure your `.env` contains your preferred configuration (database credentials, admin email/password, and JWT secret).

### 3. Launch the Stack
```bash
docker compose up -d --build
```

- 🌐 **Frontend**: [http://localhost:5173](http://localhost:5173)
- ⚙️ **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🗄️ **PostgreSQL with pgvector**: `localhost:5432` (`user: postgres`, `db: ai_interviewer`)

To inspect backend logs and migration status:
```bash
docker compose logs -f api
```

For full container documentation, see [`docs/docker.md`](docs/docker.md).

---

## 💻 Local Development (Without Docker)

### 1. Database (PostgreSQL + pgvector)
Ensure PostgreSQL 16+ is running on `localhost:5432` with the `vector` extension enabled and database `ai_interviewer` configured in `.env`.

### 2. Backend (`api/`)
```bash
cd api
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
python main.py
```
Backend API will launch on [http://localhost:8000](http://localhost:8000).

### 3. Frontend (`app/`)
```bash
cd app
npm install
npm run dev
```
Frontend will launch on [http://localhost:5173](http://localhost:5173).

---

## 🛠️ Code Quality & Verification

Before submitting pull requests or completing deployments:
```bash
# Frontend linting & formatting (strictly enforced)
cd app
npm run lint
npm run format:check
npm run build

# Backend unit & integration tests
cd ../api
pytest
```

---

## 📄 Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Comprehensive system architecture, schemas, and data flow.
- [`docs/docker.md`](docs/docker.md): Detailed Docker networking, volume persistence, and environment setup.
- [`AGENTS.md`](AGENTS.md): Strict development standards, fail-fast policies, and Git workflows.
