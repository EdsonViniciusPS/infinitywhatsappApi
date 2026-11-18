"""Async webhook forwarder with exponential backoff retry and delivery logging."""

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from typing import Any

import httpx

from app.core.database import async_session_factory
from app.models.logs import WebhookDelivery

logger = logging.getLogger(__name__)


async def forward_webhook_event(
    *,
    http_client: httpx.AsyncClient,
    instance_id: uuid.UUID | None,
    event_type: str,
    target_url: str,
    secret: str | None,
    payload: dict[str, Any],
    max_attempts: int = 3,
) -> None:
    """Deliver a webhook event to a tenant URL with retries and persist the outcome."""
    body_bytes = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Infinity-Event": event_type,
    }
    if secret:
        signature = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        headers["X-Infinity-Signature"] = f"sha256={signature}"

    http_status: int | None = None
    last_error: str | None = None
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        try:
            resp = await http_client.post(
                target_url, content=body_bytes, headers=headers, timeout=10.0
            )
            http_status = resp.status_code
            if 200 <= resp.status_code < 300:
                last_error = None
                break
            last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
        except httpx.RequestError as exc:
            last_error = str(exc)

        if attempt < max_attempts:
            await asyncio.sleep(2 ** (attempt - 1))

    if last_error:
        logger.warning(
            "Webhook delivery failed for %s (%s): %s", target_url, event_type, last_error
        )

    async with async_session_factory() as session:
        session.add(
            WebhookDelivery(
                instance_id=instance_id,
                event_type=event_type,
                target_url=target_url,
                http_status=http_status,
                attempts=attempts,
                last_error=last_error,
            )
        )
        await session.commit()
