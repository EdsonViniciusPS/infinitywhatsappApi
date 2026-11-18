"""Chats, contacts, and profile endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_evolution_client, get_owned_instance
from app.clients.evolution import EvolutionClient
from app.models.instance import Instance
from app.schemas.chat import (
    ArchiveChatRequest,
    BlockContactRequest,
    ChatPresenceRequest,
    CheckNumbersRequest,
    FindMessagesRequest,
    NumberLookupRequest,
)

router = APIRouter(prefix="/chats/{instance_name}", tags=["Chats & Contacts"])


@router.post("/check-numbers")
async def check_whatsapp_numbers(
    body: CheckNumbersRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.check_whatsapp_numbers(instance.instance_name, body.numbers)


@router.post("/profile-picture")
async def fetch_profile_picture(
    body: NumberLookupRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.fetch_profile_picture(instance.instance_name, body.number)


@router.post("/business-profile")
async def fetch_business_profile(
    body: NumberLookupRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.fetch_business_profile(instance.instance_name, body.number)


@router.get("")
async def find_chats(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.find_chats(instance.instance_name)


@router.post("/messages")
async def find_messages(
    body: FindMessagesRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.find_messages(instance.instance_name, body.model_dump())


@router.post("/contacts")
async def find_contacts(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.find_contacts(instance.instance_name)


@router.post("/archive")
async def archive_chat(
    body: ArchiveChatRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.archive_chat(instance.instance_name, body.model_dump())


@router.post("/block")
async def update_block_status(
    body: BlockContactRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.update_block_status(instance.instance_name, body.model_dump())


@router.post("/presence")
async def send_chat_presence(
    body: ChatPresenceRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.chats.update_presence(instance.instance_name, body.model_dump())
