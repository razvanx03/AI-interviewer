import json
import logging
from typing import AsyncGenerator, List, Dict, Any
import httpx
from .base import BaseLLMProvider
from .prompts import build_evaluation_report_prompt
from .constants import (
    DEFAULT_CHAT_TEMPERATURE,
    DEFAULT_EVALUATION_TEMPERATURE,
    DEFAULT_REPEAT_PENALTY,
    DEFAULT_PRESENCE_PENALTY,
    DEFAULT_FREQUENCY_PENALTY,
    DEFAULT_TOP_P,
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_READ_TIMEOUT_SECONDS,
    HTTP_WRITE_TIMEOUT_SECONDS,
    HTTP_POOL_TIMEOUT_SECONDS,
)

logger = logging.getLogger("llm.ollama")

class OllamaProvider(BaseLLMProvider):
    """
    Ollama integration provider for local LLM models (Qwen, Llama 3, DeepSeek, Mistral).
    Communicates asynchronously via HTTP with Ollama's /api/chat and supports real-time token streaming.
    All endpoint URLs and model names are injected via constructor from environment settings.
    """

    def __init__(
        self,
        base_url: str,
        model_name: str,
        temperature: float = DEFAULT_CHAT_TEMPERATURE,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = httpx.Timeout(
            connect=HTTP_CONNECT_TIMEOUT_SECONDS,
            read=HTTP_READ_TIMEOUT_SECONDS,
            write=HTTP_WRITE_TIMEOUT_SECONDS,
            pool=HTTP_POOL_TIMEOUT_SECONDS,
        )

    def _build_payload_messages(
        self, system_prompt: str, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Format messages payload with system prompt prepended."""
        payload: List[Dict[str, str]] = []
        if system_prompt and system_prompt.strip():
            payload.append({"role": "system", "content": system_prompt.strip()})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and content.strip():
                payload.append({"role": role, "content": content})
        return payload

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Generate a complete text response from Ollama."""
        url = f"{self.base_url}/api/chat"
        payload_messages = self._build_payload_messages(system_prompt, messages)

        body = {
            "model": kwargs.get("model_name", self.model_name),
            "messages": payload_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "repeat_penalty": kwargs.get("repeat_penalty", DEFAULT_REPEAT_PENALTY),
                "presence_penalty": kwargs.get("presence_penalty", DEFAULT_PRESENCE_PENALTY),
                "frequency_penalty": kwargs.get("frequency_penalty", DEFAULT_FREQUENCY_PENALTY),
                "top_p": kwargs.get("top_p", DEFAULT_TOP_P),
            },
        }

        if kwargs.get("format") == "json":
            body["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "").strip()
                return content
        except Exception as exc:
            logger.error("Ollama generate_response failed on [%s]: %s", url, exc, exc_info=True)
            raise

    async def generate_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks asynchronously in real-time from Ollama."""
        url = f"{self.base_url}/api/chat"
        payload_messages = self._build_payload_messages(system_prompt, messages)

        body = {
            "model": kwargs.get("model_name", self.model_name),
            "messages": payload_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "repeat_penalty": kwargs.get("repeat_penalty", DEFAULT_REPEAT_PENALTY),
                "presence_penalty": kwargs.get("presence_penalty", DEFAULT_PRESENCE_PENALTY),
                "frequency_penalty": kwargs.get("frequency_penalty", DEFAULT_FREQUENCY_PENALTY),
                "top_p": kwargs.get("top_p", DEFAULT_TOP_P),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=body) as response:
                    response.raise_for_status()
                    async for raw_line in response.aiter_lines():
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            chunk_text = chunk_data.get("message", {}).get("content", "")
                            if chunk_text:
                                yield chunk_text
                            if chunk_data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            logger.error("Ollama generate_stream failed on [%s]: %s", url, exc, exc_info=True)
            raise

    async def evaluate_interview(
        self,
        job_title: str,
        job_description: str,
        candidate_name: str,
        cv_raw_text: str,
        transcript: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Produce structured evaluation report for a completed interview."""
        prompt = build_evaluation_report_prompt(
            job_title=job_title,
            job_description=job_description,
            candidate_name=candidate_name,
            cv_raw_text=cv_raw_text,
            transcript=transcript,
        )

        raw_json = await self.generate_response(
            system_prompt="You are a JSON-only evaluation assistant. Output valid JSON.",
            messages=[{"role": "user", "content": prompt}],
            format="json",
            temperature=DEFAULT_EVALUATION_TEMPERATURE,
        )
        try:
            data = json.loads(raw_json)
            return data
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON evaluation from Ollama output [%s]: %s", raw_json, exc)
            raise ValueError(f"Ollama returned malformed JSON during evaluation: {exc}") from exc
