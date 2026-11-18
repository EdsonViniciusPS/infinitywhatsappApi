"""Unit tests for GeminiClient (Interactions API + Redis conversational memory)."""

from dataclasses import dataclass
from typing import Any

import pytest
from google.genai import errors as genai_errors

from app.clients.gemini import GeminiClient
from app.core.exceptions import GeminiAPIError


@dataclass
class _FakeInteraction:
    id: str
    output_text: str
    status: str = "completed"

    def model_dump(self, **_kwargs: Any) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "output_text": self.output_text}


class _FakeAsyncInteractions:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


class _FakeSDKClient:
    def __init__(self, responses: list[Any]) -> None:
        self.interactions = _FakeAsyncInteractions(responses)
        self.aio = self


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        self.ttls[key] = ex
        return True

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


async def test_create_interaction_uses_gemini_4_hydrogen_and_sanitizes_config() -> None:
    sdk = _FakeSDKClient([_FakeInteraction(id="int-100", output_text="Olá!")])
    client = GeminiClient(api_key="test-key", sdk_client=sdk)

    result = await client.create_interaction(
        input_data="Explique IA",
        system_instruction="Seja breve.",
        thinking_level="low",
        generation_config={
            "temperature": 0.9,
            "top_p": 0.8,
            "top_k": 40,
            "thinking_budget": 1024,
            "max_output_tokens": 32768,
        },
    )

    assert result["id"] == "int-100"
    assert result["model"] == "gemini-4-hydrogen"
    assert result["output_text"] == "Olá!"
    sent = sdk.interactions.calls[0]
    assert sent["model"] == "gemini-4-hydrogen"
    assert sent["input"] == "Explique IA"
    assert sent["system_instruction"] == "Seja breve."
    assert sent["store"] is True
    assert sent["generation_config"] == {
        "max_output_tokens": 32768,
        "thinking_level": "low",
    }


async def test_chat_with_contact_persists_and_reuses_redis_memory() -> None:
    redis = _FakeAsyncRedis()
    sdk = _FakeSDKClient(
        [
            _FakeInteraction(id="int-1", output_text="Prazer, João!"),
            _FakeInteraction(id="int-2", output_text="Seu nome é João."),
        ]
    )
    client = GeminiClient(
        api_key="test-key",
        redis_client=redis,
        conversation_ttl=3600,
        sdk_client=sdk,
    )

    turn1 = await client.chat_with_contact(
        instance_name="vendas",
        remote_jid="5511999999999@s.whatsapp.net",
        input_data="Oi, sou o João",
    )
    assert turn1["id"] == "int-1"
    assert turn1["previous_interaction_id"] is None
    assert sdk.interactions.calls[0].get("previous_interaction_id") is None

    memory_key = GeminiClient._memory_key("vendas", "5511999999999@s.whatsapp.net")
    assert redis.store[memory_key] == "int-1"
    assert redis.ttls[memory_key] == 3600

    turn2 = await client.chat_with_contact(
        instance_name="vendas",
        remote_jid="5511999999999@s.whatsapp.net",
        input_data="Qual é o meu nome?",
    )
    assert turn2["id"] == "int-2"
    assert turn2["previous_interaction_id"] == "int-1"
    assert sdk.interactions.calls[1]["previous_interaction_id"] == "int-1"
    assert redis.store[memory_key] == "int-2"

    cleared = await client.clear_conversation("vendas", "5511999999999@s.whatsapp.net")
    assert cleared is True
    assert memory_key not in redis.store


async def test_create_interaction_maps_api_error() -> None:
    api_err = genai_errors.APIError(403, {"error": {"message": "API key invalid"}})
    sdk = _FakeSDKClient([api_err])
    client = GeminiClient(api_key="bad-key", sdk_client=sdk)

    with pytest.raises(GeminiAPIError) as exc_info:
        await client.create_interaction(input_data="Oi")

    assert exc_info.value.status_code == 403


async def test_create_interaction_requires_api_key() -> None:
    client = GeminiClient(api_key="")
    with pytest.raises(GeminiAPIError) as exc_info:
        await client.create_interaction(input_data="Oi")

    assert exc_info.value.status_code == 500
