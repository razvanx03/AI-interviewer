from typing import AsyncGenerator, List, Dict, Any
from .base import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """
    Ollama integration provider for local models (e.g. Llama 3, Qwen 2.5, Gemma).
    Ready to connect to http://localhost:11434 via httpx/langchain_community.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3:latest"):
        self.base_url = base_url
        self.model_name = model_name

    async def generate_response(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> str:
        # TODO (Next phase): Wire httpx or LangChain Ollama wrapper
        raise NotImplementedError("OllamaProvider will be connected in Phase 2.")

    async def generate_stream(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        # TODO (Next phase): Wire token streaming from Ollama API
        raise NotImplementedError("OllamaProvider streaming will be connected in Phase 2.")
        yield ""
