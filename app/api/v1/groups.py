"""WhatsApp group management endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_evolution_client, get_owned_instance
from app.clients.evolution import EvolutionClient
from app.models.instance import Instance
from app.schemas.group import (
    GroupCreateRequest,
    GroupDescriptionRequest,
    GroupEphemeralRequest,
    GroupParticipantRequest,
    GroupPictureRequest,
    GroupSettingRequest,
    GroupSubjectRequest,
)

router = APIRouter(prefix="/groups/{instance_name}", tags=["Groups"])


@router.post("")
async def create_group(
    body: GroupCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.create(instance.instance_name, body.model_dump(exclude_none=True))


@router.get("")
async def fetch_all_groups(
    get_participants: bool = Query(default=False),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.fetch_all(instance.instance_name, get_participants=get_participants)


@router.get("/info")
async def find_group_info(
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.find_info(instance.instance_name, group_jid)


@router.put("/subject")
async def update_group_subject(
    body: GroupSubjectRequest,
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.update_subject(instance.instance_name, group_jid, body.subject)


@router.put("/description")
async def update_group_description(
    body: GroupDescriptionRequest,
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.update_description(instance.instance_name, group_jid, body.description)


@router.put("/picture")
async def update_group_picture(
    body: GroupPictureRequest,
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.update_picture(instance.instance_name, group_jid, body.image)


@router.get("/participants")
async def fetch_participants(
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.fetch_participants(instance.instance_name, group_jid)


@router.post("/participants")
async def update_participant(
    body: GroupParticipantRequest,
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.update_participant(
        instance.instance_name, group_jid, body.action, body.participants
    )


@router.get("/invite-code")
async def fetch_invite_code(
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.fetch_invite_code(instance.instance_name, group_jid)


@router.post("/revoke-invite")
async def revoke_invite_code(
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.revoke_invite_code(instance.instance_name, group_jid)


@router.post("/settings")
async def update_group_setting(
    body: GroupSettingRequest,
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.update_setting(instance.instance_name, group_jid, body.action)


@router.post("/ephemeral")
async def toggle_ephemeral(
    body: GroupEphemeralRequest,
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.toggle_ephemeral(instance.instance_name, group_jid, body.expiration)


@router.delete("/leave")
async def leave_group(
    group_jid: str = Query(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    return await evo.groups.leave(instance.instance_name, group_jid)
