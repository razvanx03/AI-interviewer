from .base import BaseLLMProvider
from .ollama_provider import OllamaProvider
from .prompts import (
    INTERVIEWER_SYSTEM_PROMPT,
    build_system_interviewer_prompt,
    build_intro_question_prompt,
    build_evaluation_report_prompt,
)
from .constants import (
    DEFAULT_CHAT_TEMPERATURE,
    DEFAULT_EVALUATION_TEMPERATURE,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_READ_TIMEOUT_SECONDS,
)

def get_llm_provider(
    base_url: str,
    model_name: str,
) -> BaseLLMProvider:
    """
    Factory creating configured LLM provider instance (OllamaProvider).
    Requires explicit base_url and model_name from configuration.
    """
    return OllamaProvider(base_url=base_url, model_name=model_name)

__all__ = [
    "BaseLLMProvider",
    "OllamaProvider",
    "get_llm_provider",
    "INTERVIEWER_SYSTEM_PROMPT",
    "build_system_interviewer_prompt",
    "build_intro_question_prompt",
    "build_evaluation_report_prompt",
    "DEFAULT_CHAT_TEMPERATURE",
    "DEFAULT_EVALUATION_TEMPERATURE",
    "HTTP_CONNECT_TIMEOUT_SECONDS",
    "HTTP_READ_TIMEOUT_SECONDS",
]
