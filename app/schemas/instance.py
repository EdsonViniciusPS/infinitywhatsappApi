"""Schemas for WhatsApp instance management."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InstanceCreate(BaseModel):
    instance_name: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    qrcode: bool = True
    number: str | None = Field(default=None, description="Número para pairing code, se aplicável")
    integration: Literal["WHATSAPP-BAILEYS", "WHATSAPP-BUSINESS"] = "WHATSAPP-BAILEYS"
    reject_call: bool = False
    groups_ignore: bool = False
    always_online: bool = False
    read_messages: bool = False
    read_status: bool = False
    webhook_url: str | None = None
    webhook_secret: str | None = None
    webhook_events: list[str] = Field(default_factory=list)
    ai_enabled: bool = False
    ai_model: str | None = None
    ai_system_prompt: str | None = Field(default=None, max_length=2000)


class InstanceRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    instance_name: str
    evo_instance_id: str | None
    status: str
    webhook_url: str | None
    webhook_events: list[str]
    ai_enabled: bool
    ai_model: str | None
    ai_system_prompt: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InstanceSettingsUpdate(BaseModel):
    rejectCall: bool = False
    msgCall: str = ""
    groupsIgnore: bool = False
    alwaysOnline: bool = False
    readMessages: bool = False
    readStatus: bool = False
    syncFullHistory: bool = False


class PresenceUpdate(BaseModel):
    presence: Literal["available", "unavailable"]
