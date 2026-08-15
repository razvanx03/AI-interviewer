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
