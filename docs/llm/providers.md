# LLM Providers (`llm/base.py`, `llm/ollama_provider.py`, `llm/__init__.py`)

## 1. `BaseLLMProvider`
Abstract base class defining the AI contract:
- `generate_response(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> str`
- `generate_stream(system_prompt: str, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]`
- `evaluate_interview(job_title: str, job_description: str, candidate_name: str, cv_raw_text: str, transcript: List[Dict[str, str]]) -> Dict[str, Any]`

## 2. `OllamaProvider` (Active Production Provider)
Integrates local LLM models (e.g., `hf.co/radi04/qwen3-8b-cs-interviewer-merge-v1-150-q4:Q4_K_M`, `qwen2.5:7b`, `llama3.2`) via Ollama's HTTP API (`http://localhost:11434`):
- **Asynchronous Token Streaming**: Consumes Ollama's `POST /api/chat` with `stream: true` to yield real-time tokens over Server-Sent Events (SSE).
- **JSON Evaluation Mode**: Executes evaluation prompts with `format: "json"` to produce structured hiring scores and summaries.
- **Anti-Repetition & Sampling Controls**:
  - `temperature`: `0.7` for dialogue variety, `0.2` for JSON evaluation.
  - `repeat_penalty`: `1.18` (llama.cpp / Ollama native) preventing verbatim token loops.
  - `presence_penalty`: `0.6` encouraging topic transitions.
  - `frequency_penalty`: `0.5` reducing repetitive verbal patterns.
  - `top_p`: `0.9` (nucleus sampling) ensuring coherent probability tail cutoff.
- **Configurable**: Configured via `OLLAMA_BASE_URL` and `DEFAULT_LLM_MODEL` in `.env`.

## 3. `get_llm_provider(base_url, model_name)`
Factory function in `llm/__init__.py` providing the configured `OllamaProvider` instance.
