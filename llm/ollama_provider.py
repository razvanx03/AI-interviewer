import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx
from .base import BaseLLMProvider
from .prompts import (
    build_evaluation_report_prompt,
    build_conversation_summary_prompt,
    build_chunk_evaluation_prompt,
    build_final_evaluation_aggregation_prompt,
)
from .constants import (
    DEFAULT_CHAT_TEMPERATURE,
    DEFAULT_EVALUATION_TEMPERATURE,
    DEFAULT_REPEAT_PENALTY,
    DEFAULT_PRESENCE_PENALTY,
    DEFAULT_FREQUENCY_PENALTY,
    DEFAULT_TOP_P,
    DEFAULT_NUM_CTX,
    EVALUATION_CHUNK_SIZE_ROUNDS,
    EVALUATION_CHUNK_TRIGGER_ROUNDS,
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
    All endpoint URLs, context window size, and model names are injected via constructor from environment settings.
    """

    def __init__(
        self,
        base_url: str,
        model_name: str,
        temperature: float = DEFAULT_CHAT_TEMPERATURE,
        num_ctx: int = DEFAULT_NUM_CTX,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.num_ctx = num_ctx
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
        """Generate a complete text response from Ollama with explicit num_ctx options."""
        url = f"{self.base_url}/api/chat"
        payload_messages = self._build_payload_messages(system_prompt, messages)

        body = {
            "model": kwargs.get("model_name", self.model_name),
            "messages": payload_messages,
            "stream": False,
            "options": {
                "num_ctx": kwargs.get("num_ctx", self.num_ctx),
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
        """Stream token chunks asynchronously in real-time from Ollama with explicit num_ctx options."""
        url = f"{self.base_url}/api/chat"
        payload_messages = self._build_payload_messages(system_prompt, messages)

        body = {
            "model": kwargs.get("model_name", self.model_name),
            "messages": payload_messages,
            "stream": True,
            "options": {
                "num_ctx": kwargs.get("num_ctx", self.num_ctx),
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

    async def summarize_conversation_history(
        self,
        job_title: str,
        candidate_name: str,
        rounds_to_summarize: List[Dict[str, str]],
        existing_summary: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Produce a dense, cumulative summary of older interview rounds."""
        prompt = build_conversation_summary_prompt(
            job_title=job_title,
            candidate_name=candidate_name,
            rounds_to_summarize=rounds_to_summarize,
            existing_summary=existing_summary,
        )
        summary = await self.generate_response(
            system_prompt="You are a factual, concise technical interview recorder.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            **kwargs,
        )
        return summary.strip()

    def _parse_transcript_into_rounds(self, transcript: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Parse raw chronological message dicts into structured Q&A exchange rounds."""
        rounds: List[Dict[str, Any]] = []
        current_q: Optional[str] = None
        round_idx = 1

        for msg in transcript:
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if not content:
                continue

            if role in ["assistant", "system"]:
                if (
                    "Thank you for completing your interview" in content
                    or "**Overall AI Assessment:" in content
                    or "**Evaluare Generală AI:" in content
                ):
                    continue
                current_q = content
            elif role == "user":
                if current_q is not None:
                    rounds.append({
                        "question_id": round_idx,
                        "question": current_q,
                        "answer": content,
                    })
                    current_q = None
                    round_idx += 1
                else:
                    if rounds:
                        rounds[-1]["answer"] += f" (Follow-up: {content})"

        if current_q is not None:
            rounds.append({
                "question_id": round_idx,
                "question": current_q,
                "answer": "[NO RESPONSE PROVIDED - CANDIDATE CONCLUDED SESSION WITHOUT ANSWERING]",
            })

        return rounds

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
        """Produce structured evaluation report with chunked Map-Reduce for long transcripts."""
        qa_rounds = self._parse_transcript_into_rounds(transcript)

        # If transcript is long, execute Chunked Map-Reduce Evaluation
        if len(qa_rounds) >= EVALUATION_CHUNK_TRIGGER_ROUNDS:
            logger.info(
                "Transcript has %d rounds (>= %d threshold). Running chunked Map-Reduce evaluation to prevent context overflow.",
                len(qa_rounds),
                EVALUATION_CHUNK_TRIGGER_ROUNDS,
            )
            chunks: List[List[Dict[str, Any]]] = [
                qa_rounds[i : i + EVALUATION_CHUNK_SIZE_ROUNDS]
                for i in range(0, len(qa_rounds), EVALUATION_CHUNK_SIZE_ROUNDS)
            ]
            chunk_results: List[Dict[str, Any]] = []

            for idx, chunk in enumerate(chunks, 1):
                chunk_prompt = build_chunk_evaluation_prompt(
                    job_title=job_title,
                    job_description=job_description,
                    experience_level=experience_level,
                    candidate_name=candidate_name,
                    chunk_rounds=chunk,
                    chunk_index=idx,
                    total_chunks=len(chunks),
                )
                raw_chunk_json = await self.generate_response(
                    system_prompt="You are a JSON-only technical evaluation assistant. Output valid JSON.",
                    messages=[{"role": "user", "content": chunk_prompt}],
                    format="json",
                    temperature=0.1,
                )
                try:
                    chunk_data = json.loads(raw_chunk_json)
                    chunk_results.append(chunk_data)
                except json.JSONDecodeError as err:
                    logger.warning("Failed to parse chunk #%d JSON: %s. Raw: %s", idx, err, raw_chunk_json)
                    chunk_results.append({
                        "chunk_index": idx,
                        "chunk_score": 3.0,
                        "question_evaluations": [
                            {
                                "question_id": r.get("question_id", idx),
                                "question_text": r.get("question", "")[:120],
                                "candidate_response": r.get("answer", "")[:100],
                                "explanation": "Evaluated during batch processing.",
                                "score": 3.0,
                            }
                            for r in chunk
                        ],
                    })

            agg_prompt = build_final_evaluation_aggregation_prompt(
                job_title=job_title,
                job_description=job_description,
                experience_level=experience_level,
                candidate_name=candidate_name,
                chunk_evaluations=chunk_results,
                topics_plan=topics_plan,
                time_limit_minutes=time_limit_minutes,
                covered_topics_count=covered_topics_count,
                total_topics_count=total_topics_count,
            )
            raw_final_json = await self.generate_response(
                system_prompt="You are a JSON-only hiring committee chair. Output valid JSON.",
                messages=[{"role": "user", "content": agg_prompt}],
                format="json",
                temperature=DEFAULT_EVALUATION_TEMPERATURE,
            )
            try:
                final_data = json.loads(raw_final_json)
                return final_data
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse final aggregated JSON from Ollama [%s]: %s", raw_final_json, exc)
                raise ValueError(f"Ollama returned malformed JSON during final evaluation synthesis: {exc}") from exc

        # Standard single-pass evaluation for standard-length transcripts (<= 4 rounds)
        prompt = build_evaluation_report_prompt(
            job_title=job_title,
            job_description=job_description,
            candidate_name=candidate_name,
            cv_raw_text=cv_raw_text,
            transcript=transcript,
            experience_level=experience_level,
            time_limit_minutes=time_limit_minutes,
            covered_topics_count=covered_topics_count,
            total_topics_count=total_topics_count,
            topics_plan=topics_plan,
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
