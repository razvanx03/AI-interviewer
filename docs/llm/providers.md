# LLM Providers (`llm/base.py`, `llm/mock_provider.py`, `llm/ollama_provider.py`)

## 1. `BaseLLMProvider`
Abstract base class defining:
- `generate_response(system_prompt, messages, **kwargs) -> str`
- `generate_stream(system_prompt, messages, **kwargs) -> AsyncGenerator[str, None]`

## 2. `MockLLMProvider`
Deterministic mock provider used for fast local testing and prototyping:
- Generates simulated questions based on interview stage.
- Yields simulated token chunks with 40ms interval.

## 3. `OllamaProvider`
Target provider for running local open-weights models (e.g. Llama 3 8B, Qwen 2.5 7B, Gemma 2 9B):
- Connects to Ollama's local HTTP API (`http://localhost:11434`).
- Supports local inference without sending candidate CV data to third-party cloud APIs.
