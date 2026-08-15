# System Architecture

## 1. System Overview

The **AI-Powered Job Interviewer** is a privacy-centric, decoupled multi-service platform for conducting automated technical job interviews tailored directly to candidate resumes and job role requirements.

```
+-------------------------------------------------------------+
|                         Browser / Client                    |
|  - React 19 + TypeScript + Vite                             |
|  - shadcn/ui Design System (Radix UI Primitives)            |
|  - LocalStorage Session & History Persistence               |
|  - Shareable URL Routing (/interview/:id)                   |
+------------------------------+------------------------------+
                               |
                   HTTP / REST | WebSocket Streaming
                               v
+-------------------------------------------------------------+
|                         api/ (FastAPI)                      |
|  - Pydantic v2 Request/Response Validation                  |
|  - Clean Layered Endpoints & Services                       |
|  - Real-time Token Streaming & WS Handlers                  |
+------------------------------+------------------------------+
                               |
               Abstract BaseLLMProvider Interface
                               v
+-------------------------------------------------------------+
|                         llm/ (AI Engine)                    |
|  - MockLLMProvider (Simulated Streaming & Testing)          |
|  - OllamaProvider Stub (Ready for Local Llama 3 / Qwen)     |
|  - Structured Prompt Templates & Interview State            |
|  - Future: pgvector RAG & PyMuPDF CV Extraction             |
+-------------------------------------------------------------+
```

---

## 2. Directory Separation & Responsibility

- **`app/`**: Single-Page React application. Handles UI rendering, interview creation wizard, CV drag-and-drop, interactive chat room, and browser-side `localStorage` caching. (Docs: [`docs/app/`](app/INDEX.md))
- **`api/`**: Asynchronous Python backend powered by FastAPI. Exposes REST and WebSocket endpoints, manages session state, and coordinates with the AI engine. (Docs: [`docs/api/`](api/INDEX.md))
- **`llm/`**: Standalone AI & Prompt Engineering layer. Decouples model providers behind an abstract interface (`BaseLLMProvider`). (Docs: [`docs/llm/`](llm/INDEX.md))
- **`docs/`**: Mirrored documentation tree reflecting each component and folder in the application.

---

## 3. Pragmatic Abstraction Guidelines

1. **Purposeful Interfaces**: Abstractions are intentionally used where they provide real swappability (e.g. `BaseLLMProvider` for mock vs Ollama, storage services for in-memory vs PostgreSQL).
2. **Avoid Over-Engineering**: Do not create speculative abstractions without a clear architectural need. Keep implementations concise and maintainable.
3. **Current Scope**: `llm/` contains only interfaces, prompt templates, and mock providers for the initial prototype. Full Ollama, LangChain, and pgvector integrations are planned for the next phase.
