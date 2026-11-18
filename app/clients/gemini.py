"""Async Google Gemini client built on google-genai (Interactions API) with Redis memory."""

import logging
from typing import Any

from google import genai
from google.genai import errors as genai_errors

from app.core.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)

_DEPRECATED_GEN_CONFIG_KEYS = frozenset({"temperature", "top_p", "top_k", "thinking_budget"})


class GeminiClient:
    """Async wrapper over google-genai Interactions API with per-contact Redis memory."""

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-4-hydrogen",
        redis_client: Any = None,
        conversation_ttl: int = 86400,
        sdk_client: Any = None,
    ) -> None:
        self._api_key = api_key
        self.default_model = default_model
        self._redis = redis_client
        self._conversation_ttl = conversation_ttl
        self._sdk_client = sdk_client

    def _get_client(self) -> Any:
        if self._sdk_client is not None:
            return self._sdk_client
        if not self._api_key:
            raise GeminiAPIError("GEMINI_API_KEY não configurada.", status_code=500)
        self._sdk_client = genai.Client(api_key=self._api_key)
        return self._sdk_client

    @staticmethod
    def _sanitize_generation_config(
        generation_config: dict[str, Any] | None,
        thinking_level: str | None,
    ) -> dict[str, Any] | None:
        """Strip legacy sampling/budget keys and apply thinking_level for Gemini 4."""
        cfg = {
            k: v
            for k, v in (generation_config or {}).items()
            if k not in _DEPRECATED_GEN_CONFIG_KEYS
        }
        if thinking_level:
            cfg["thinking_level"] = thinking_level
        return cfg or None

    @staticmethod
    def _memory_key(instance_name: str, remote_jid: str) -> str:
        return f"infinity:gemini:last_interaction:{instance_name}:{remote_jid}"

    async def get_previous_interaction_id(
        self, instance_name: str, remote_jid: str
    ) -> str | None:
        """Fetch the last interaction ID for a WhatsApp contact from Redis."""
        if self._redis is None:
            return None
        try:
            value = await self._redis.get(self._memory_key(instance_name, remote_jid))
            return str(value) if value else None
        except Exception as exc:
            logger.warning("Falha ao ler memória Gemini no Redis: %s", exc)
            return None

    async def set_previous_interaction_id(
        self, instance_name: str, remote_jid: str, interaction_id: str
    ) -> None:
        """Persist the latest interaction ID for a WhatsApp contact in Redis with TTL."""
        if self._redis is None:
            return
        try:
            await self._redis.set(
                self._memory_key(instance_name, remote_jid),
                interaction_id,
                ex=self._conversation_ttl,
            )
        except Exception as exc:
            logger.warning("Falha ao gravar memória Gemini no Redis: %s", exc)

    async def clear_conversation(self, instance_name: str, remote_jid: str) -> bool:
        """Delete stored conversation memory for a WhatsApp contact from Redis."""
        if self._redis is None:
            return False
        try:
            deleted = await self._redis.delete(self._memory_key(instance_name, remote_jid))
            return bool(deleted)
        except Exception as exc:
            logger.warning("Falha ao limpar memória Gemini no Redis: %s", exc)
            return False

    async def create_interaction(
        self,
        *,
        input_data: str | list[dict[str, Any]],
        model: str | None = None,
        system_instruction: str | None = None,
        previous_interaction_id: str | None = None,
        thinking_level: str | None = None,
        generation_config: dict[str, Any] | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        """Call Google Gemini Interactions API asynchronously and normalize the response."""
        client = self._get_client()
        target_model = model or self.default_model

        kwargs: dict[str, Any] = {
            "model": target_model,
            "input": input_data,
            "store": store,
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if previous_interaction_id:
            kwargs["previous_interaction_id"] = previous_interaction_id

        sanitized_cfg = self._sanitize_generation_config(generation_config, thinking_level)
        if sanitized_cfg:
            kwargs["generation_config"] = sanitized_cfg

        try:
            interaction = await client.aio.interactions.create(**kwargs)
        except genai_errors.APIError as exc:
            code = getattr(exc, "code", None)
            status_code = code if isinstance(code, int) and 400 <= code < 500 else 502
            raise GeminiAPIError(
                f"Gemini API retornou erro: {exc}",
                status_code=status_code,
                details={"code": code, "message": str(exc)},
            ) from exc
        except GeminiAPIError:
            raise
        except Exception as exc:
            raise GeminiAPIError(
                f"Falha de comunicação com a Gemini API: {exc}",
                status_code=502,
            ) from exc

        raw = (
            interaction.model_dump(mode="json", exclude_none=True)
            if hasattr(interaction, "model_dump")
            else {}
        )
        return {
            "id": getattr(interaction, "id", None),
            "model": target_model,
            "status": str(getattr(interaction, "status", "completed")),
            "output_text": getattr(interaction, "output_text", None) or "",
            "raw": raw,
        }

    async def chat_with_contact(
        self,
        *,
        instance_name: str,
        remote_jid: str,
        input_data: str | list[dict[str, Any]],
        system_instruction: str | None = None,
        model: str | None = None,
        thinking_level: str | None = None,
        generation_config: dict[str, Any] | None = None,
        reset_memory: bool = False,
    ) -> dict[str, Any]:
        """Run a multi-turn Gemini interaction anchored to the contact's Redis state."""
        if reset_memory:
            await self.clear_conversation(instance_name, remote_jid)
            prev_id = None
        else:
            prev_id = await self.get_previous_interaction_id(instance_name, remote_jid)

        result = await self.create_interaction(
            input_data=input_data,
            model=model,
            system_instruction=system_instruction,
            previous_interaction_id=prev_id,
            thinking_level=thinking_level,
            generation_config=generation_config,
            store=True,
        )

        interaction_id = result.get("id")
        if isinstance(interaction_id, str) and interaction_id:
            await self.set_previous_interaction_id(instance_name, remote_jid, interaction_id)

        return {**result, "previous_interaction_id": prev_id}
