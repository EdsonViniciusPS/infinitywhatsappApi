"""Schemas for WhatsApp group management."""

from typing import Literal

from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    participants: list[str] = Field(..., min_length=1)


class GroupSubjectRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)


class GroupDescriptionRequest(BaseModel):
    description: str


class GroupPictureRequest(BaseModel):
    image: str = Field(..., description="URL pública ou Base64 da imagem")


class GroupParticipantRequest(BaseModel):
    action: Literal["add", "remove", "promote", "demote"]
    participants: list[str] = Field(..., min_length=1)


class GroupSettingRequest(BaseModel):
    action: Literal["announcement", "not_announcement", "locked", "unlocked"]


class GroupEphemeralRequest(BaseModel):
    expiration: int = Field(..., ge=0, description="Segundos (0 para desativar)")
