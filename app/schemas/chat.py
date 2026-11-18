"""Schemas for chats and contacts."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class CheckNumbersRequest(BaseModel):
    numbers: list[str] = Field(..., min_length=1)


class NumberLookupRequest(BaseModel):
    number: str


class FindMessagesRequest(BaseModel):
    where: dict[str, Any] = Field(default_factory=dict)
    page: int | None = Field(default=1, ge=1)
    offset: int | None = Field(default=20, ge=1, le=100)


class ArchiveChatRequest(BaseModel):
    lastMessage: dict[str, Any]
    chat: str
    archive: bool


class BlockContactRequest(BaseModel):
    number: str
    status: Literal["block", "unblock"]


class ChatPresenceRequest(BaseModel):
    number: str
    delay: int = Field(default=1200, ge=0)
    presence: Literal["composing", "recording", "paused"]
