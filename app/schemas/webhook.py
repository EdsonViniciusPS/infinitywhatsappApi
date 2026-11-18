"""Schemas for webhook configuration and delivery logs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class InstanceWebhookConfig(BaseModel):
    webhook_url: HttpUrl | None = None
    webhook_secret: str | None = None
    webhook_events: list[str] = []


class WebhookDeliveryRead(BaseModel):
    id: uuid.UUID
    instance_id: uuid.UUID | None
    event_type: str
    target_url: str
    http_status: int | None
    attempts: int
    last_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
