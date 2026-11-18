"""Evolution API v2 — Chats, contacts, and profile endpoints."""

from typing import Any

from app.clients.evolution.base import EvolutionBaseClient


class ChatsClient:
    """Client for Evolution API chat and contact endpoints."""

    def __init__(self, base: EvolutionBaseClient) -> None:
        self._base = base

    async def check_whatsapp_numbers(self, instance_name: str, numbers: list[str]) -> Any:
        """Check whether phone numbers are registered on WhatsApp."""
        return await self._base.request(
            "POST", f"/chat/whatsappNumbers/{instance_name}", json={"numbers": numbers}
        )

    async def fetch_profile_picture(self, instance_name: str, number: str) -> Any:
        """Fetch profile picture URL for a contact or group."""
        return await self._base.request(
            "POST", f"/chat/fetchProfilePictureUrl/{instance_name}", json={"number": number}
        )

    async def fetch_business_profile(self, instance_name: str, number: str) -> Any:
        """Fetch WhatsApp Business profile details."""
        return await self._base.request(
            "POST", f"/chat/fetchBusinessProfile/{instance_name}", json={"number": number}
        )

    async def find_chats(self, instance_name: str) -> Any:
        """List chats for the instance."""
        return await self._base.request("POST", f"/chat/findChats/{instance_name}")

    async def find_messages(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Search messages in chats."""
        return await self._base.request(
            "POST", f"/chat/findMessages/{instance_name}", json=payload
        )

    async def find_contacts(self, instance_name: str, payload: dict[str, Any] | None = None) -> Any:
        """Search contacts."""
        return await self._base.request(
            "POST", f"/chat/findContacts/{instance_name}", json=payload or {}
        )

    async def archive_chat(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Archive or unarchive a chat."""
        return await self._base.request("POST", f"/chat/archiveChat/{instance_name}", json=payload)

    async def update_block_status(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Block or unblock a contact."""
        return await self._base.request(
            "POST", f"/message/updateBlockStatus/{instance_name}", json=payload
        )

    async def update_presence(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send chat presence (composing, recording, paused)."""
        return await self._base.request(
            "POST", f"/chat/sendPresence/{instance_name}", json=payload
        )
