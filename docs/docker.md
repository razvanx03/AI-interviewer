# Docker Multi-Container Architecture & Operations Guide

> **Official reference for containerized deployment of the AI Interviewer platform.**

---

## 1. Overview

The application is orchestrated as a multi-container microservices environment using `docker-compose.yml`:

| Service / Image | Container Name | Technology | Internal Port | Host Port | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`postgres`** | `postgres` | PostgreSQL 16 + `pgvector` | `5432` | `5432` | Relational & Vector database for sessions, messages, and CV embeddings |
| **`api`** | `api` | FastAPI (Python 3.11) | `8000` | `8000` | REST API, SSE Streaming pipeline, and LLM Orchestrator |
| **`app`** | `app` | React + Vite + Tailwind | `5173` | `5173` | Responsive UI SPA |

---

## 2. LLM Serving Strategy (Local Dev vs Containerized Production)

- **Development Phase (Current)**:
  - Ollama runs natively on the host machine to leverage direct NVIDIA GPU acceleration (`RTX 3060 Ti`, CUDA/Tensor Cores) without WSL2 virtualization overhead.
  - The `api` container communicates with the host Ollama instance via `http://host.docker.internal:11434` (with *Expose Ollama to the network* enabled).
- **Production Deployment (Future Phase)**:
  - An isolated `ollama` container (`ollama/ollama:latest`) will be included directly in `docker-compose.yml` with persistent volume storage for models (`ollama_models:/root/.ollama`) and GPU driver passthrough (`deploy.resources.reservations.devices`).

---

## 3. Operations Commands

### Prerequisites
Copy `.env.example` to `.env` before starting containers (all variables are strictly validated):
```bash
cp .env.example .env
```

### Start all containers in background
```bash
docker compose up -d --build
```

### Stop all containers
```bash
docker compose down
```

### View live logs across containers
```bash
docker compose logs -f
```

---

## 4. URLs and Access Points

- **Frontend Application**: `http://localhost:5173`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`
- **PostgreSQL Database**: `localhost:5432` (`user: postgres`, `password: postgres`, `db: ai_interviewer`)
- **Ollama LLM (Host)**: `http://localhost:11434` (accessible from Docker via `http://host.docker.internal:11434`)

---

## 5. Development & Hot-Reload

Both `api/` and `app/` are mounted as bind volumes into the containers:
- Any change to Python files in `api/` immediately reloads FastAPI via `uvicorn --reload`.
- Any change to React/TypeScript files in `app/` immediately hot-reloads the browser via Vite HMR.
