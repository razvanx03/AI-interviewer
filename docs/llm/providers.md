# LLM Providers (`llm/base.py`, `llm/ollama_provider.py`, `llm/__init__.py`)

## 1. `BaseLLMProvider`
Abstract base class defining the AI contract:
- `generate_response(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str`
- `generate_stream(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]`
- `summarize_conversation_history(job_title: str, candidate_name: str, rounds_to_summarize: List[Dict[str, str]], existing_summary: Optional[str] = None) -> str`
- `evaluate_interview(...) -> Dict[str, Any]`

## 2. `OllamaProvider` (Active Production Provider)
Integrates local LLM models (e.g., `hf.co/radi04/qwen3-8b-cs-interviewer-merge-v1-150-q4:Q4_K_M`, `qwen2.5:7b`, `llama3.2`) via Ollama's HTTP API (`http://localhost:11434`):
- **Explicit Context Allocation (`num_ctx`)**: Passes `num_ctx` (default `8192`) in `options` to allocate exact memory window in Ollama.
- **Progressive Summarization**: When conversations approach context threshold (>60% of `num_ctx`), older Q&A rounds are compressed into a persistent summary stored in PostgreSQL (`interviews.conversation_summary`).
- **Asynchronous Token Streaming**: Consumes Ollama's `POST /api/chat` with `stream: true` to yield real-time tokens over Server-Sent Events (SSE).
- **Chunked Map-Reduce Evaluation & Resilient JSON Extraction**: Long interview transcripts (>4 rounds) are split into chunks of 3-4 rounds, evaluated partially in batches, and synthesized by a Reduce aggregation prompt into the final JSON report. Uses strict fail-fast validation to raise explicit runtime errors without masking failures or fabricating fake evaluation scores.
- **Strict Fail-Fast Embeddings (`embed_text`, `embed_documents`)**: Uses `nomic-embed-text` (768 dimensions) via Ollama `/api/embed` or `/api/embeddings`. Fails fast with descriptive `RuntimeError` if Ollama is unreachable or the model is missing (zero pseudo-random or zero-vector fallbacks).
- **Anti-Repetition & Sampling Controls**:
  - `temperature`: `0.7` for dialogue variety, `0.2` for JSON evaluation.
  - `repeat_penalty`: `1.18` (llama.cpp / Ollama native) preventing verbatim token loops.
  - `presence_penalty`: `0.6` encouraging topic transitions.
  - `frequency_penalty`: `0.5` reducing repetitive verbal patterns.
  - `top_p`: `0.9` (nucleus sampling) ensuring coherent probability tail cutoff.
- **Configurable**: Configured via `OLLAMA_BASE_URL`, `DEFAULT_LLM_MODEL`, and `OLLAMA_NUM_CTX` in `.env`.

## 3. `get_llm_provider(base_url, model_name, num_ctx)`
Factory function in `llm/__init__.py` providing the configured `OllamaProvider` instance with context window support.

