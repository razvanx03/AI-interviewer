# AI Developer & Agent Instructions (`AGENTS.md`)

> **CRITICAL INSTRUCTIONS FOR FUTURE AI AGENTS WORKING ON THIS REPOSITORY**

---

## 1. Documentation Synchronization (MANDATORY)

The `docs/` directory is structured as a **direct mirror** of the project directories (`docs/app/`, `docs/api/`, `docs/llm/`):

Whenever you make changes to this codebase:
1. **Always update the matching markdown documentation in `docs/`**:
   - `docs/ARCHITECTURE.md`: High-level system design, data flow, and directory map.
   - `docs/app/`: When frontend components, pages, hooks, state, types, or routing change.
   - `docs/api/`: When FastAPI endpoints, schemas, services, or config change.
   - `docs/llm/`: When prompt templates, model providers, or RAG pipelines change.
2. **Do NOT add redundant README files** inside subdirectories (`app/`, `api/`, `llm/`). Maintain only the single root `README.md` for GitHub presentation and use `docs/` for all technical specifications.

---

## 2. Frontend UI & Code Quality Constraints (STRICT RESTRAINT)

1. **Stick to shadcn/ui Components**:
   - Always use or compose **shadcn/ui** components (located in `app/src/components/ui/`) based on accessible Radix UI primitives.
   - **Do NOT** write raw ad-hoc CSS or create custom arbitrary CSS class files.
   - **Do NOT** invent custom ad-hoc styling paradigms when a standard shadcn component exists (e.g. `Button`, `Card`, `Dialog`, `Input`, `Textarea`, `Badge`, `Separator`, `ScrollArea`, `Tabs`, `Toast/Sonner`).
   - If a new UI primitive is required, scaffold it using standard shadcn/ui conventions inside `app/src/components/ui/`.
2. **ESLint & Prettier Compliance (MANDATORY)**:
   - **ESLint** and **Prettier** are strictly enforced for all frontend code in `app/`.
   - Before finishing any task on `app/`, you MUST ensure:
     - `npm run lint` passes with **0 errors**.
     - `npm run format:check` (or `npm run format`) passes.
     - `npm run build` succeeds without TypeScript or bundling issues.
3. **Aesthetic Excellence**:
   - Maintain clean, modern typography, subtle borders (`border-border`), balanced whitespace, fluid responsiveness, and purposeful micro-interactions.

---

## 3. Architectural Separation Rules

1. **`app/`**: Contains only the frontend Single Page Application (React + Vite + TypeScript). No Python or backend dependencies.
2. **`api/`**: Contains the FastAPI REST and WebSocket server with clean top-level folders (`core/`, `endpoints/`, `schemas/`, `services/`, `router.py`, `main.py`).
3. **`llm/`**: Contains the standalone AI provider abstractions, prompt templates, and local model wrappers (Ollama/pgvector). `api/` interacts with `llm/` through `BaseLLMProvider`.
4. **Current Phase Scope for `llm/`**: The `llm/` module currently contains only abstract interfaces, prompt templates, and mock providers. Actual Ollama, LangChain, embeddings, and pgvector integrations will be implemented in subsequent phases.

---

## 4. Purposeful & Pragmatic Abstraction Guidelines

1. **Do Not Avoid Necessary Abstractions**:
   - This project is intentionally designed to evolve incrementally from mock implementations to production-grade integrations (Ollama, PostgreSQL, pgvector, LangChain RAG).
   - Use clean abstractions, base interfaces, and service layers wherever they enable swappability without rewriting API routes or frontend contracts (e.g., `BaseLLMProvider` → `MockLLMProvider` now, `OllamaProvider` later; session storage interfaces → in-memory now, PostgreSQL later).
2. **Avoid Abstractions for Abstraction's Sake**:
   - Every interface, service, repository, or factory must serve a clear architectural purpose.
   - Avoid creating unnecessary layers of indirection, speculative factories, or premature generalizations when a simple, well-typed interface suffices.
3. **Modularity and Extensibility**:
   - Keep the codebase modular, readable, maintainable, and straightforward to extend without excessive cognitive overhead.

---

## 5. Clean Architecture & Legacy Code Removal (MANDATORY)

1. **Delete Obsolete Implementations Completely**:
   - Whenever you make a significant change or migrate to a newer architecture (e.g. migrating full localStorage sessions to database persistence, switching from polling to SSE streaming), **always delete the old, deprecated code, functions, fallback mock data stores, and obsolete localStorage keys**.
   - **Never leave dual persistence mechanisms or dead legacy paths** running alongside new features, as they cause infinite loops, state de-synchronization, and bloated client memory.
   - Clean up any legacy localStorage keys automatically (e.g. `localStorage.removeItem('ai_interviewer_sessions_v1')`) when the client loads.

---

## 6. Docker Containerization Synchronization (MANDATORY)

1. **Keep Docker Configuration Always In-Sync**:
   - Whenever dependencies (`api/requirements.txt`, `app/package.json`), environment variables (`.env`, `config.py`), ports, or service architectures change:
     - **Always update `docker-compose.yml`**, `api/Dockerfile`, `app/Dockerfile`, and `.dockerignore` files.
     - **Always verify that `docker compose up --build` continues to work cleanly** and launches all 3 services (`frontend`, `backend`, `db`).
   - Document any new containerized services, volume mounts, or networking changes in `docs/docker.md`.

---

## 7. Strict Prohibition of Dataset Overfitting, Hardcoding & Fake Benchmarks (ZERO TOLERANCE)

1. **Never Overfit to Test Datasets or Specific Files**:
   - AI agents are **STRICTLY FORBIDDEN** from hardcoding heuristics, cities, companies, candidate names, technologies, or artificial scoring ladders tailored to specific test files, sample datasets, or wizard mocks.
   - Never write logic that expects a particular candidate, city (e.g., "Sibiu"), company, or stack (e.g., "Ruby on Rails", ".NET and Node.js") to achieve predetermined scores or rankings.
2. **Generic, Bidirectional, and Symmetric Systems Only**:
   - All matching, scoring, and classification pipelines must be completely role-agnostic and dynamically driven by the user's inputs (`job_title`, `job_description`, candidate texts).
   - If the system is evaluated on a Data Engineering role, a Data Engineer must rank top; if evaluated on an Embedded role, an Embedded engineer must rank top; if on a Web role, a Web engineer must rank top.
3. **Word Boundary Enforcement for Technical Matching**:
   - Never use naive substring checks (e.g. `'rest' in text` or `'go' in text`), as they create catastrophic false positives (matching "REST" in "Somarest" or "Go" in general Romanian words).
   - Always enforce exact word boundaries (`\b`) and handle punctuation-bearing symbols (`.NET`, `C#`, `C++`) safely.
4. **Authentic AI & RAG Evaluation**:
   - Prompts must remain generic and never state false role assumptions (e.g., never instruct an LLM that "You are hiring for a Web Backend Developer" when the job title could be any engineering role).

---

## 8. Strict Prohibition of Silent Fallbacks, Mocks in Production, and Error Masking (STRICT FAIL-FAST POLICY)

1. **Zero Silent Fallbacks Across the Entire Codebase (ZERO TOLERANCE)**:
   - If an AI model is not installed, Ollama is unreachable, pgvector/database fails, a network call times out, or document parsing fails, the code **MUST FAIL FAST AND RAISE AN EXPLICIT EXCEPTION** (`RuntimeError`, `ValueError`, `HTTPException`).
   - AI agents are **STRICTLY FORBIDDEN** from catching exceptions and falling back to:
     - Fake or deterministic hash-based vectors (`_fallback_embedding`, zero-vectors `[0.0] * 768`).
     - Canned AI messages pretending the interviewer responded.
     - Fabricated evaluation reports or default scores (e.g. fake `7.0/10 (Hire)`).
     - Heuristic regex parsers pretending LLM structured extraction succeeded.
2. **No Mock Providers in Production Paths**:
   - `MockLLMProvider` or mock engines are strictly restricted to `api/tests/` for deterministic unit test fixtures.
   - Under no circumstances may application factories (`get_llm_provider`), endpoints, or services (`InterviewService`, `ScreeningService`, `CVParser`) fall back to mock providers when a model or service fails.
3. **Expose Real Errors Immediately**:
   - Always let errors bubble up with actionable diagnostic messages (e.g. stating which model is missing and prompting `ollama pull <model>`).
   - Never mask, swallow, or disguise operational errors as successful operations.

---

## 9. Git & Remote Repository Workflow (STRICT PROHIBITION OF AUTONOMOUS PUSH)

1. **Strict Prohibition of Autonomous `git push` (ZERO TOLERANCE)**:
   - AI agents are **STRICTLY FORBIDDEN** from running `git push` commands autonomously to remote repositories (GitHub/origin).
   - All commits made by the agent must remain local. The user retains absolute authority and control over reviewing changes and publishing them to remote repositories.
   - Once changes are committed and verified locally, provide the user with the exact branch name and manual `git push` command to run in their own interactive shell.
2. **Work Exclusively on the User's Active Branch**:
   - AI agents must **ALWAYS work strictly on the active git branch that the user is currently on** when work begins.
   - Never switch branches, create speculative side-branches, or modify git branch pointers without the user's explicit request.


