"""Evolution API v2 — Group management endpoints."""

from typing import Any

from app.clients.evolution.base import EvolutionBaseClient


class GroupsClient:
    """Client for Evolution API group endpoints."""

    def __init__(self, base: EvolutionBaseClient) -> None:
        self._base = base

    async def create(self, instance_name: str, payload: dict[str, Any]) -> Any:
        """Create a new WhatsApp group."""
        return await self._base.request("POST", f"/group/create/{instance_name}", json=payload)

    async def fetch_all(self, instance_name: str, get_participants: bool = False) -> Any:
        """Fetch all groups for the instance."""
        return await self._base.request(
            "GET",
            f"/group/fetchAllGroups/{instance_name}",
            params={"getParticipants": str(get_participants).lower()},
        )

    async def find_info(self, instance_name: str, group_jid: str) -> Any:
        """Find group metadata by JID."""
        return await self._base.request(
            "GET", f"/group/findGroupInfos/{instance_name}", params={"groupJid": group_jid}
        )

    async def update_subject(self, instance_name: str, group_jid: str, subject: str) -> Any:
        """Update group name/subject."""
        return await self._base.request(
            "POST",
            f"/group/updateGroupSubject/{instance_name}",
            params={"groupJid": group_jid},
            json={"subject": subject},
        )

    async def update_description(
        self, instance_name: str, group_jid: str, description: str
    ) -> Any:
        """Update group description."""
        return await self._base.request(
            "POST",
            f"/group/updateGroupDescription/{instance_name}",
            params={"groupJid": group_jid},
            json={"description": description},
        )

    async def update_picture(self, instance_name: str, group_jid: str, image: str) -> Any:
        """Update group profile picture."""
        return await self._base.request(
            "POST",
            f"/group/updateGroupPicture/{instance_name}",
            params={"groupJid": group_jid},
            json={"image": image},
        )

    async def fetch_participants(self, instance_name: str, group_jid: str) -> Any:
        """List group participants."""
        return await self._base.request(
            "GET", f"/group/participants/{instance_name}", params={"groupJid": group_jid}
        )

    async def update_participant(
        self, instance_name: str, group_jid: str, action: str, participants: list[str]
    ) -> Any:
        """Add, remove, promote, or demote group participants."""
        return await self._base.request(
            "POST",
            f"/group/updateParticipant/{instance_name}",
            params={"groupJid": group_jid},
            json={"action": action, "participants": participants},
        )

    async def fetch_invite_code(self, instance_name: str, group_jid: str) -> Any:
        """Get group invite link/code."""
        return await self._base.request(
            "GET", f"/group/inviteCode/{instance_name}", params={"groupJid": group_jid}
        )

    async def revoke_invite_code(self, instance_name: str, group_jid: str) -> Any:
        """Revoke and regenerate group invite link/code."""
        return await self._base.request(
            "POST", f"/group/revokeInviteCode/{instance_name}", params={"groupJid": group_jid}
        )

    async def update_setting(self, instance_name: str, group_jid: str, action: str) -> Any:
        """Update group settings (announcement, not_announcement, locked, unlocked)."""
        return await self._base.request(
            "POST",
            f"/group/updateSetting/{instance_name}",
            params={"groupJid": group_jid},
            json={"action": action},
        )

    async def toggle_ephemeral(self, instance_name: str, group_jid: str, expiration: int) -> Any:
        """Set disappearing messages expiration in seconds (0 to disable)."""
        return await self._base.request(
            "POST",
            f"/group/toggleEphemeral/{instance_name}",
            params={"groupJid": group_jid},
            json={"expiration": expiration},
        )

    async def leave(self, instance_name: str, group_jid: str) -> Any:
        """Leave a group."""
        return await self._base.request(
            "DELETE", f"/group/leaveGroup/{instance_name}", params={"groupJid": group_jid}
        )
