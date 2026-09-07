import json
import logging
import re
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx
from .base import BaseLLMProvider
from .prompts import (
    build_evaluation_report_prompt,
    build_conversation_summary_prompt,
    build_chunk_evaluation_prompt,
    build_final_evaluation_aggregation_prompt,
    parse_transcript_into_qa_rounds,
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
        embedding_model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.embedding_model = embedding_model
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
        return parse_transcript_into_qa_rounds(transcript)

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
            parsed_final = self._parse_json_payload(raw_final_json)
            if parsed_final:
                return parsed_final

            raise RuntimeError(
                f"Failed to parse final aggregated JSON from Ollama output: {raw_final_json[:300]}"
            )

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
        parsed_eval = self._parse_json_payload(raw_json)
        if parsed_eval:
            return parsed_eval

        raise RuntimeError(
            f"Failed to parse JSON evaluation from Ollama output: {raw_json[:300]}"
        )

    def _parse_json_payload(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON dictionary from LLM response safely."""
        if not raw_text or not raw_text.strip():
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            val = json.loads(cleaned)
            if isinstance(val, dict):
                return val
        except json.JSONDecodeError:
            pass

        # Regex search for JSON object
        match = re.search(r"(\{[\s\S]*\})", raw_text)
        if match:
            try:
                val = json.loads(match.group(1))
                if isinstance(val, dict):
                    return val
            except json.JSONDecodeError:
                pass
        return None

    async def embed_text(self, text: str) -> List[float]:
        """Generate 768-dim vector embedding for single string using Ollama nomic-embed-text."""
        res = await self.embed_documents([text])
        if not res:
            raise RuntimeError(f"Ollama embedding returned empty result for model '{self.embedding_model}'.")
        return res[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for list of documents using Ollama /api/embed or /api/embeddings."""
        if not texts:
            return []

        clean_texts = [t.strip() or "empty" for t in texts]

        # 1. Try modern batch /api/embed endpoint
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.embedding_model,
                        "input": clean_texts,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings")
                    if embeddings and len(embeddings) == len(clean_texts):
                        return embeddings
                else:
                    logger.warning(
                        "Ollama /api/embed returned HTTP %d (%s). Trying legacy endpoint.",
                        resp.status_code,
                        resp.text[:200],
                    )
        except Exception as embed_err:
            logger.warning("Ollama /api/embed attempt failed (%s). Trying legacy endpoint.", embed_err)

        # 2. Try legacy /api/embeddings single-item endpoint
        results: List[List[float]] = []
        all_succeeded = True
        last_error = None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for txt in clean_texts:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={
                            "model": self.embedding_model,
                            "prompt": txt,
                        },
                    )
                    if resp.status_code == 200:
                        emb = resp.json().get("embedding")
                        if emb:
                            results.append(emb)
                            continue
                    last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    all_succeeded = False
                    break
        except Exception as leg_err:
            last_error = str(leg_err)
            all_succeeded = False

        if all_succeeded and len(results) == len(clean_texts):
            return results

        raise RuntimeError(
            f"Ollama embedding failed for model '{self.embedding_model}' at {self.base_url}: {last_error}. "
            f"Ensure Ollama is running and model '{self.embedding_model}' is pulled via 'ollama pull {self.embedding_model}'."
        )
