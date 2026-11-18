"""Schemas for WhatsApp message sending and actions."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class SendTextRequest(BaseModel):
    number: str = Field(..., description="Número com DDI+DDD ou JID (ex: 5511999999999)")
    text: str = Field(..., min_length=1)
    delay: int | None = Field(default=None, ge=0)
    linkPreview: bool = True
    mentionsEveryOne: bool = False
    mentioned: list[str] | None = None
    quoted: dict[str, Any] | None = None


class SendMediaRequest(BaseModel):
    number: str
    mediatype: Literal["image", "video", "document"]
    mimetype: str | None = None
    caption: str | None = None
    media: str = Field(..., description="URL pública ou string Base64")
    fileName: str | None = None
    delay: int | None = Field(default=None, ge=0)


class SendAudioRequest(BaseModel):
    number: str
    audio: str = Field(..., description="URL pública ou string Base64")
    delay: int | None = Field(default=None, ge=0)
    encoding: bool = True


class SendStickerRequest(BaseModel):
    number: str
    sticker: str = Field(..., description="URL pública ou string Base64")
    delay: int | None = Field(default=None, ge=0)


class SendLocationRequest(BaseModel):
    number: str
    name: str
    address: str
    latitude: float
    longitude: float


class ContactItem(BaseModel):
    fullName: str
    wuid: str
    phoneNumber: str
    organization: str | None = None
    email: str | None = None
    url: str | None = None


class SendContactRequest(BaseModel):
    number: str
    contact: list[ContactItem] = Field(..., min_length=1)


class SendReactionRequest(BaseModel):
    key: dict[str, Any]
    reaction: str


class SendPollRequest(BaseModel):
    number: str
    name: str
    selectableCount: int = Field(default=1, ge=1)
    values: list[str] = Field(..., min_length=2)


class SendListRequest(BaseModel):
    number: str
    title: str
    description: str
    buttonText: str
    footerText: str = ""
    sections: list[dict[str, Any]]


class SendButtonsRequest(BaseModel):
    number: str
    title: str
    description: str
    footer: str = ""
    buttons: list[dict[str, Any]]


class SendStatusRequest(BaseModel):
    type: Literal["text", "image", "video", "audio"]
    content: str
    caption: str | None = None
    backgroundColor: str | None = None
    font: int | None = None
    allContacts: bool = True
    statusJidList: list[str] | None = None


class UpdateMessageRequest(BaseModel):
    number: str
    key: dict[str, Any]
    text: str


class DeleteMessageRequest(BaseModel):
    id: str
    remoteJid: str
    fromMe: bool = True
    participant: str | None = None


class MarkAsReadRequest(BaseModel):
    readMessages: list[dict[str, Any]]
