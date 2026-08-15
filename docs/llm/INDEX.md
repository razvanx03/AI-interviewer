# AI Engine & LLM Layer (`llm/`) Architecture

## 1. Overview
The `llm/` module isolates all AI interactions, model provider integrations, prompt templates, and vector search bindings.

## 2. Current Phase Scope
- **Current State**: Contains only abstract interfaces (`BaseLLMProvider`), prompt engineering templates (`prompts.py`), and mock generators (`MockLLMProvider`).
- **Future Integration**: Actual local Ollama model execution (Llama 3, Qwen 2.5), LangChain pipelines, embedding generation (`nomic-embed-text`), and pgvector vector search will be implemented in subsequent phases.

## 3. Directory Structure Mirror
- [`providers.md`](providers.md): `BaseLLMProvider`, `MockLLMProvider`, `OllamaProvider`
- [`prompts.md`](prompts.md): `INTERVIEWER_SYSTEM_PROMPT`, `CV_EXTRACTION_PROMPT`
- [`rag.md`](rag.md): PostgreSQL + pgvector integration roadmap

## 4. Abstract Interface
All providers implement `BaseLLMProvider`, ensuring the backend API routes and services remain decoupled from the underlying model provider implementation.
