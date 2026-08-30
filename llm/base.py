from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional

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

    @abstractmethod
    async def summarize_conversation_history(
        self,
        job_title: str,
        candidate_name: str,
        rounds_to_summarize: List[Dict[str, str]],
        existing_summary: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Produce a dense, cumulative summary of older interview rounds."""
        pass

    @abstractmethod
    async def evaluate_interview(
        self,
        job_title: str,
        job_description: str,
        candidate_name: str,
        cv_raw_text: str,
        transcript: List[Dict[str, str]],
        experience_level: str = "mid",
        time_limit_minutes: Optional[int] = None,
        covered_topics_count: Optional[int] = None,
        total_topics_count: Optional[int] = None,
        topics_plan: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Produce structured evaluation report for a completed interview."""
        pass
