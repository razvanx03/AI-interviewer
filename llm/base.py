from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any

class BaseLLMProvider(ABC):
    """
    Abstract interface for AI/LLM providers (Mock, Ollama, LangChain, etc.)
    Ensures modularity so model providers can be swapped without touching API routes.
    """

    @abstractmethod
    async def generate_response(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> str:
        """Generate complete text response."""
        pass

    @abstractmethod
    async def generate_stream(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks in real time."""
        pass
