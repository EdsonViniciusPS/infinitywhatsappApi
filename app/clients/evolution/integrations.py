"""Evolution API v2 — Integrations (Typebot, Chatwoot, OpenAI, Dify)."""

from typing import Any

from app.clients.evolution.base import EvolutionBaseClient


class IntegrationsClient:
    """Unified client for Evolution API native integrations."""

    def __init__(self, base: EvolutionBaseClient) -> None:
        self._base = base

    async def configure(
        self, integration: str, instance_name: str, payload: dict[str, Any]
    ) -> Any:
        """Create or update an integration (typebot, chatwoot, openai, dify)."""
        return await self._base.request(
            "POST", f"/{integration}/set/{instance_name}", json=payload
        )

    async def find(self, integration: str, instance_name: str) -> Any:
        """Get integration configuration for an instance."""
        return await self._base.request("GET", f"/{integration}/find/{instance_name}")

    async def delete(self, integration: str, instance_name: str, integration_id: str) -> Any:
        """Delete an integration configuration."""
        return await self._base.request(
            "DELETE", f"/{integration}/delete/{integration_id}/{instance_name}"
        )
