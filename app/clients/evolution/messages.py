"""Evolution API v2 — Message sending and manipulation endpoints."""

from typing import Any

from app.clients.evolution.base import EvolutionBaseClient


class MessagesClient:
    """Client for Evolution API message endpoints."""

    def __init__(self, base: EvolutionBaseClient) -> None:
        self._base = base

    async def send_text(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send a text message."""
        return await self._base.request("POST", f"/message/sendText/{instance_name}", json=payload)

    async def send_media(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send image, video, or document media."""
        return await self._base.request("POST", f"/message/sendMedia/{instance_name}", json=payload)

    async def send_audio(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send narrated WhatsApp audio (PTT)."""
        return await self._base.request(
            "POST", f"/message/sendWhatsAppAudio/{instance_name}", json=payload
        )

    async def send_sticker(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send a sticker."""
        return await self._base.request(
            "POST", f"/message/sendSticker/{instance_name}", json=payload
        )

    async def send_location(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send a geographic location."""
        return await self._base.request(
            "POST", f"/message/sendLocation/{instance_name}", json=payload
        )

    async def send_contact(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send one or more vCard contacts."""
        return await self._base.request(
            "POST", f"/message/sendContact/{instance_name}", json=payload
        )

    async def send_reaction(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send an emoji reaction to a message."""
        return await self._base.request(
            "POST", f"/message/sendReaction/{instance_name}", json=payload
        )

    async def send_poll(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send a poll."""
        return await self._base.request("POST", f"/message/sendPoll/{instance_name}", json=payload)

    async def send_list(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send an interactive list message."""
        return await self._base.request("POST", f"/message/sendList/{instance_name}", json=payload)

    async def send_buttons(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Send an interactive buttons message."""
        return await self._base.request(
            "POST", f"/message/sendButtons/{instance_name}", json=payload
        )

    async def send_status(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Post a WhatsApp Status / Story."""
        return await self._base.request(
            "POST", f"/message/sendStatus/{instance_name}", json=payload
        )

    async def update_message(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Edit a previously sent message."""
        return await self._base.request(
            "POST", f"/chat/updateMessage/{instance_name}", json=payload
        )

    async def delete_message(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Delete a message for everyone."""
        return await self._base.request(
            "DELETE", f"/chat/deleteMessageForEveryone/{instance_name}", json=payload
        )

    async def mark_as_read(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Mark messages as read."""
        return await self._base.request(
            "POST", f"/chat/markMessageAsRead/{instance_name}", json=payload
        )
