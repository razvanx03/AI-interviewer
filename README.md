# AI-Powered Job Interviewer

An autonomous technical job interviewer web application that tailors questions based on candidate resumes and job role requirements.

![AI Interviewer Architecture](https://img.shields.io/badge/Frontend-React%20%2B%20shadcn%2Fui-blue)
![API Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Pydantic-green)
![Local AI](https://img.shields.io/badge/AI-Ollama%20%2F%20Local%20LLM-purple)

---

## Architecture Overview

```
AI-interviewer/
├── app/                      # React 19 + TypeScript + Vite + shadcn/ui
├── api/                      # FastAPI Python REST & WebSocket backend
├── llm/                      # AI provider layer (Mock, Ollama, Prompts)
├── docs/                     # Mirrored technical documentation
│   ├── ARCHITECTURE.md
│   ├── app/                  # Mirrored frontend component & state docs
│   ├── api/                  # Mirrored backend endpoints & service docs
│   └── llm/                  # Mirrored AI engine & RAG docs
├── AGENTS.md                 # Developer & AI assistant guidelines
└── README.md
```

For in-depth architecture and development details, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Features

- **Custom Interview Wizard**: Specify target job role, company, seniority level, requirements, and drop a CV file (PDF/DOCX/TXT).
- **Shareable URL**: Each session receives a unique 8-character token (e.g. `/interview/k8d9f1a2`).
- **Interactive AI Chat Room**: Live technical screening with dynamic evaluation, follow-up questions, and performance summary.
- **LocalStorage History**: Browser stores previous interview transcripts and links for quick reference without requiring user accounts.
- **Privacy & Local AI Ready**: Decoupled architecture designed for local Ollama models (Llama 3, Qwen 2.5, Gemma) and PostgreSQL + pgvector.

---

## Quick Start

### 1. Frontend (`app/`)

```bash
cd app
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 2. Backend (`api/`)

```bash
cd api
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Developer Guidelines

Please review [`AGENTS.md`](AGENTS.md) before making contributions. All UI modifications must strictly adhere to **shadcn/ui** components, code must pass ESLint & Prettier checks, and technical documentation in `docs/` must be updated synchronously.
