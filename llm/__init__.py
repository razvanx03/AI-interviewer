from .base import BaseLLMProvider
from .ollama_provider import OllamaProvider
from .prompts import (
    INTERVIEWER_SYSTEM_PROMPT,
    build_system_interviewer_prompt,
    build_intro_prompt,
    build_first_question_prompt,
    build_clarification_response_prompt,
    build_both_response_prompt,
    build_refusal_response_prompt,
    build_next_question_prompt,
    build_extract_topics_prompt,
    build_screening_prompt,
    build_rag_screening_prompt,
    build_conversation_summary_prompt,
    build_chunk_evaluation_prompt,
    build_final_evaluation_aggregation_prompt,
    build_evaluation_report_prompt,
    parse_transcript_into_qa_rounds,
    is_wrapup_or_evaluation_message,
)
from .chunking import SemanticTextSplitter, TimelineExtractor
from .constants import (
    DEFAULT_CHAT_TEMPERATURE,
    DEFAULT_EVALUATION_TEMPERATURE,
    DEFAULT_NUM_CTX,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_READ_TIMEOUT_SECONDS,
)

def get_llm_provider(
    base_url: str,
    model_name: str,
    num_ctx: int = DEFAULT_NUM_CTX,
) -> BaseLLMProvider:
    """
    Factory creating configured LLM provider instance (OllamaProvider).
    Requires explicit base_url, model_name, and context window size.
    """
    return OllamaProvider(base_url=base_url, model_name=model_name, num_ctx=num_ctx)

__all__ = [
    "BaseLLMProvider",
    "OllamaProvider",
    "get_llm_provider",
    "INTERVIEWER_SYSTEM_PROMPT",
    "build_system_interviewer_prompt",
    "build_intro_prompt",
    "build_first_question_prompt",
    "build_clarification_response_prompt",
    "build_both_response_prompt",
    "build_refusal_response_prompt",
    "build_next_question_prompt",
    "build_extract_topics_prompt",
    "build_screening_prompt",
    "build_rag_screening_prompt",
    "build_conversation_summary_prompt",
    "build_chunk_evaluation_prompt",
    "build_final_evaluation_aggregation_prompt",
    "build_evaluation_report_prompt",
    "parse_transcript_into_qa_rounds",
    "is_wrapup_or_evaluation_message",
    "SemanticTextSplitter",
    "TimelineExtractor",
    "DEFAULT_CHAT_TEMPERATURE",
    "DEFAULT_EVALUATION_TEMPERATURE",
    "HTTP_CONNECT_TIMEOUT_SECONDS",
    "HTTP_READ_TIMEOUT_SECONDS",
]

