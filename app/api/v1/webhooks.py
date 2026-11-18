"""Webhook receiver from Evolution API and per-instance forwarding configuration."""

import logging
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_instance
from app.clients.evolution import EvolutionClient
from app.clients.gemini import GeminiClient
from app.core.config import get_settings
from app.core.database import async_session_factory, get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import verify_constant_time
from app.models.instance import Instance
from app.models.logs import MessageLog, WebhookDelivery
from app.schemas.webhook import InstanceWebhookConfig, WebhookDeliveryRead
from app.services.webhook_forwarder import forward_webhook_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _extract_incoming_message(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Extract (remote_jid, text) from a direct incoming messages.upsert payload."""
    data = payload.get("data")
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None

    key = data.get("key")
    if not isinstance(key, dict) or key.get("fromMe"):
        return None

    remote_jid = key.get("remoteJid")
    if (
        not isinstance(remote_jid, str)
        or not remote_jid
        or remote_jid.endswith("@g.us")
        or remote_jid == "status@broadcast"
    ):
        return None

    message = data.get("message")
    if not isinstance(message, dict):
        return None

    text = message.get("conversation")
    if not isinstance(text, str):
        extended = message.get("extendedTextMessage")
        if isinstance(extended, dict):
            text = extended.get("text")

    if not isinstance(text, str) or not text.strip():
        return None
    return remote_jid, text.strip()


async def _auto_reply_with_gemini(
    *,
    http_client: httpx.AsyncClient,
    redis_client: Any,
    instance_id: uuid.UUID,
    instance_name: str,
    remote_jid: str,
    incoming_text: str,
    system_prompt: str | None,
    model: str | None,
) -> None:
    """Generate a multi-turn Gemini response with Redis memory, send it, and log both messages."""
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        return

    gemini = GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        default_model=settings.GEMINI_MODEL,
        redis_client=redis_client,
        conversation_ttl=settings.GEMINI_CONVERSATION_TTL_SECONDS,
    )
    evo = EvolutionClient(
        http_client=http_client,
        base_url=settings.EVOLUTION_API_URL,
        api_key=settings.EVOLUTION_API_KEY,
    )
    try:
        result = await gemini.chat_with_contact(
            instance_name=instance_name,
            remote_jid=remote_jid,
            input_data=incoming_text,
            system_instruction=system_prompt,
            model=model,
        )
        reply_text = str(result.get("output_text", "")).strip()
        if not reply_text:
            return

        await evo.messages.send_text(
            instance_name, {"number": remote_jid, "text": reply_text}
        )
        async with async_session_factory() as session:
            session.add(
                MessageLog(
                    instance_id=instance_id,
                    direction="inbound",
                    remote_jid=remote_jid,
                    message_type="text",
                    status="received",
                    payload_summary={"length": len(incoming_text)},
                )
            )
            session.add(
                MessageLog(
                    instance_id=instance_id,
                    direction="outbound",
                    remote_jid=remote_jid,
                    message_type="ai_auto_reply",
                    status="sent",
                    payload_summary={
                        "model": result.get("model"),
                        "interaction_id": result.get("id"),
                        "previous_interaction_id": result.get("previous_interaction_id"),
                    },
                )
            )
            await session.commit()
    except Exception:
        logger.exception(
            "Falha no auto-atendimento Gemini para %s (%s)", instance_name, remote_jid
        )


@router.post("/evolution")
async def receive_evolution_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    secret: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Receive global events from Evolution API, update instance state, and forward to tenant."""
    settings = get_settings()
    if not secret or not verify_constant_time(secret, settings.EVOLUTION_WEBHOOK_SECRET):
        raise UnauthorizedError("Segredo de webhook inválido.")

    payload: dict[str, Any] = await request.json()
    event_type = str(payload.get("event", "unknown"))
    instance_name = payload.get("instance")

    if not isinstance(instance_name, str) or not instance_name:
        return {"status": "ignored"}

    stmt = select(Instance).where(Instance.instance_name == instance_name)
    instance = (await db.execute(stmt)).scalar_one_or_none()
    if not instance:
        return {"status": "instance_not_registered"}

    # Update local status on connection.update events
    if event_type == "connection.update" and isinstance(payload.get("data"), dict):
        state = payload["data"].get("state")
        if isinstance(state, str):
            instance.status = state
            await db.flush()

    if instance.webhook_url:
        allowed_events = instance.webhook_events or []
        if not allowed_events or event_type in allowed_events:
            background_tasks.add_task(
                forward_webhook_event,
                http_client=request.app.state.http_client,
                instance_id=instance.id,
                event_type=event_type,
                target_url=instance.webhook_url,
                secret=instance.webhook_secret,
                payload=payload,
            )

    if event_type == "messages.upsert" and instance.ai_enabled:
        extracted = _extract_incoming_message(payload)
        if extracted:
            remote_jid, incoming_text = extracted
            background_tasks.add_task(
                _auto_reply_with_gemini,
                http_client=request.app.state.http_client,
                redis_client=getattr(request.app.state, "redis", None),
                instance_id=instance.id,
                instance_name=instance.instance_name,
                remote_jid=remote_jid,
                incoming_text=incoming_text,
                system_prompt=instance.ai_system_prompt,
                model=instance.ai_model,
            )

    return {"status": "accepted"}


@router.put("/{instance_name}/config")
async def configure_instance_webhook(
    body: InstanceWebhookConfig,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Configure the tenant's destination webhook URL and subscribed events for an instance."""
    instance.webhook_url = str(body.webhook_url) if body.webhook_url else None
    instance.webhook_secret = body.webhook_secret
    instance.webhook_events = body.webhook_events
    await db.flush()
    return {
        "instance_name": instance.instance_name,
        "webhook_url": instance.webhook_url,
        "webhook_events": instance.webhook_events,
    }


@router.get("/{instance_name}/deliveries", response_model=list[WebhookDeliveryRead])
async def list_webhook_deliveries(
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookDelivery]:
    """List recent webhook delivery attempts for an instance."""
    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.instance_id == instance.id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
    )
    return list((await db.execute(stmt)).scalars().all())
