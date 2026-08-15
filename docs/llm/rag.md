# RAG & Vector Retrieval (`llm/rag.md`)

## 1. Overview
Roadmap for augmenting the interview system with retrieval-augmented generation (RAG).

## 2. Recommended Strategy (Hybrid Approach)
- **Direct Context for Resumes**: Because CVs are 1–3 pages (~500–2,500 tokens), the entire parsed CV and Job Description are passed directly into the LLM system prompt for holistic context.
- **pgvector Retrieval**: Use PostgreSQL + pgvector for:
  - Technical rubrics & question libraries.
  - Large corporate competency frameworks.
  - Multi-page project portfolios or code sample evaluation.

## 3. Embedding Pipeline
- Local embedding model: `nomic-embed-text` via Ollama.
- Vector store: PostgreSQL with `pgvector` extension.
