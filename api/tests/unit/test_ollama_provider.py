import math
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from llm.ollama_provider import OllamaProvider


class TestOllamaProviderUnit:
    """Unit tests for OllamaProvider payload formatting, JSON parsing, and vector embeddings."""

    def test_build_payload_messages(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model_name="qwen2.5:7b")
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": ""},  # empty should be filtered
        ]
        payload = provider._build_payload_messages("System instruction", messages)

        assert len(payload) == 3
        assert payload[0] == {"role": "system", "content": "System instruction"}
        assert payload[1] == {"role": "user", "content": "Hello!"}
        assert payload[2] == {"role": "assistant", "content": "Hi there!"}

    def test_build_payload_messages_no_system_prompt(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model_name="qwen2.5:7b")
        payload = provider._build_payload_messages("", [{"role": "user", "content": "Question"}])
        assert len(payload) == 1
        assert payload[0] == {"role": "user", "content": "Question"}

    def test_parse_json_payload_clean(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model_name="qwen2.5:7b")
        data = {"score": 8.5, "status": "pass"}
        parsed = provider._parse_json_payload(json.dumps(data))
        assert parsed == data

    def test_parse_json_payload_markdown_wrapped(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model_name="qwen2.5:7b")
        raw = "```json\n{\"overall_score\": 9.0, \"recommendation\": \"hire\"}\n```"
        parsed = provider._parse_json_payload(raw)
        assert parsed is not None
        assert parsed["overall_score"] == 9.0
        assert parsed["recommendation"] == "hire"

    def test_parse_json_payload_embedded_in_text(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model_name="qwen2.5:7b")
        raw = "Here is the candidate report:\n{\"match_score\": 85}\nHope this helps!"
        parsed = provider._parse_json_payload(raw)
        assert parsed is not None
        assert parsed["match_score"] == 85

    def test_parse_json_payload_invalid(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model_name="qwen2.5:7b")
        assert provider._parse_json_payload("") is None
        assert provider._parse_json_payload("No JSON here at all.") is None

    @pytest.mark.asyncio
    async def test_embed_text_fails_on_network_error(self):
        provider = OllamaProvider(base_url="http://invalid-host:11434", model_name="qwen2.5:7b")
        with pytest.raises(RuntimeError, match="Ollama embedding failed"):
            await provider.embed_text("Python backend microservices")

    @pytest.mark.asyncio
    async def test_embed_documents_batch_fails_on_network_error(self):
        provider = OllamaProvider(base_url="http://invalid-host:11434", model_name="qwen2.5:7b")
        docs = ["Doc 1 about React", "Doc 2 about .NET Core", "Doc 3 about Docker"]
        with pytest.raises(RuntimeError, match="Ollama embedding failed"):
            await provider.embed_documents(docs)

    @pytest.mark.asyncio
    async def test_embed_documents_empty_list(self):
        provider = OllamaProvider(base_url="http://invalid-host:11434", model_name="qwen2.5:7b")
        result = await provider.embed_documents([])
        assert result == []

