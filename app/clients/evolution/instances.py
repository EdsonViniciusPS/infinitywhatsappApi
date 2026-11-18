"""Evolution API v2 — Instance management endpoints."""

from typing import Any

from app.clients.evolution.base import EvolutionBaseClient


class InstancesClient:
    """Client for Evolution API instance lifecycle and settings."""

    def __init__(self, base: EvolutionBaseClient) -> None:
        self._base = base

    async def create(self, payload: dict[str, Any]) -> Any:
        """Create a new WhatsApp instance."""
        return await self._base.request("POST", "/instance/create", json=payload)

    async def fetch_all(self, instance_name: str | None = None) -> Any:
        """Fetch all instances or filter by instanceName."""
        params = {"instanceName": instance_name} if instance_name else None
        return await self._base.request("GET", "/instance/fetchInstances", params=params)

    async def connect(self, instance_name: str, number: str | None = None) -> Any:
        """Connect an instance and retrieve QR Code / pairing code."""
        params = {"number": number} if number else None
        return await self._base.request("GET", f"/instance/connect/{instance_name}", params=params)

    async def connection_state(self, instance_name: str) -> Any:
        """Get current connection state (open, connecting, close)."""
        return await self._base.request("GET", f"/instance/connectionState/{instance_name}")

    async def restart(self, instance_name: str) -> Any:
        """Restart an instance."""
        return await self._base.request("POST", f"/instance/restart/{instance_name}")

    async def logout(self, instance_name: str) -> Any:
        """Logout from WhatsApp session on an instance."""
        return await self._base.request("DELETE", f"/instance/logout/{instance_name}")

    async def delete(self, instance_name: str) -> Any:
        """Delete an instance permanently."""
        return await self._base.request("DELETE", f"/instance/delete/{instance_name}")

    async def set_presence(self, instance_name: str, presence: str) -> Any:
        """Set instance presence (available | unavailable)."""
        return await self._base.request(
            "POST", f"/instance/setPresence/{instance_name}", json={"presence": presence}
        )

    async def set_settings(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Update instance behavior settings."""
        return await self._base.request("POST", f"/settings/set/{instance_name}", json=payload)

    async def get_settings(self, instance_name: str) -> Any:
        """Retrieve instance behavior settings."""
        return await self._base.request("GET", f"/settings/find/{instance_name}")
