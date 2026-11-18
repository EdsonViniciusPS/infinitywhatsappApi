"""Evolution API v2 — Webhooks and event transport endpoints."""

from typing import Any

from app.clients.evolution.base import EvolutionBaseClient


class WebhooksClient:
    """Client for Evolution API webhook, WebSocket, RabbitMQ, and SQS configuration."""

    def __init__(self, base: EvolutionBaseClient) -> None:
        self._base = base

    async def set_webhook(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Configure per-instance webhook in Evolution API."""
        return await self._base.request("POST", f"/webhook/set/{instance_name}", json=payload)

    async def find_webhook(self, instance_name: str) -> Any:
        """Retrieve per-instance webhook configuration."""
        return await self._base.request("GET", f"/webhook/find/{instance_name}")

    async def set_websocket(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Configure WebSocket events for an instance."""
        return await self._base.request("POST", f"/websocket/set/{instance_name}", json=payload)

    async def set_rabbitmq(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Configure RabbitMQ events for an instance."""
        return await self._base.request("POST", f"/rabbitmq/set/{instance_name}", json=payload)

    async def set_sqs(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Configure AWS SQS events for an instance."""
        return await self._base.request("POST", f"/sqs/set/{instance_name}", json=payload)
