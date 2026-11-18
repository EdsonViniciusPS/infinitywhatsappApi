"""WhatsApp messaging endpoints covering all Evolution API message types."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_evolution_client, get_owned_instance
from app.clients.evolution import EvolutionClient
from app.core.database import get_db
from app.models.instance import Instance
from app.models.logs import MessageLog
from app.schemas.message import (
    DeleteMessageRequest,
    MarkAsReadRequest,
    SendAudioRequest,
    SendButtonsRequest,
    SendContactRequest,
    SendListRequest,
    SendLocationRequest,
    SendMediaRequest,
    SendPollRequest,
    SendReactionRequest,
    SendStatusRequest,
    SendStickerRequest,
    SendTextRequest,
    UpdateMessageRequest,
)

router = APIRouter(prefix="/messages/{instance_name}", tags=["Messages"])


async def _log_outbound(
    db: AsyncSession,
    instance: Instance,
    remote_jid: str,
    message_type: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        MessageLog(
            instance_id=instance.id,
            direction="outbound",
            remote_jid=remote_jid,
            message_type=message_type,
            status="sent",
            payload_summary={"keys": list(payload.keys())},
        )
    )


@router.post("/text")
async def send_text(
    body: SendTextRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_text(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "text", payload)
    return resp


@router.post("/media")
async def send_media(
    body: SendMediaRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_media(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, body.mediatype, payload)
    return resp


@router.post("/audio")
async def send_audio(
    body: SendAudioRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_audio(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "audio", payload)
    return resp


@router.post("/sticker")
async def send_sticker(
    body: SendStickerRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_sticker(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "sticker", payload)
    return resp


@router.post("/location")
async def send_location(
    body: SendLocationRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_location(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "location", payload)
    return resp


@router.post("/contact")
async def send_contact(
    body: SendContactRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_contact(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "contact", payload)
    return resp


@router.post("/reaction")
async def send_reaction(
    body: SendReactionRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.messages.send_reaction(instance.instance_name, body.model_dump())


@router.post("/poll")
async def send_poll(
    body: SendPollRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_poll(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "poll", payload)
    return resp


@router.post("/list")
async def send_list(
    body: SendListRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_list(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "list", payload)
    return resp


@router.post("/buttons")
async def send_buttons(
    body: SendButtonsRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    payload = body.model_dump(exclude_none=True)
    resp = await evo.messages.send_buttons(instance.instance_name, payload)
    await _log_outbound(db, instance, body.number, "buttons", payload)
    return resp


@router.post("/status")
async def send_status(
    body: SendStatusRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.messages.send_status(
        instance.instance_name, body.model_dump(exclude_none=True)
    )


@router.put("")
async def update_message(
    body: UpdateMessageRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.messages.update_message(instance.instance_name, body.model_dump())


@router.delete("")
async def delete_message(
    body: DeleteMessageRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.messages.delete_message(
        instance.instance_name, body.model_dump(exclude_none=True)
    )


@router.post("/mark-read")
async def mark_as_read(
    body: MarkAsReadRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.messages.mark_as_read(instance.instance_name, body.model_dump())
