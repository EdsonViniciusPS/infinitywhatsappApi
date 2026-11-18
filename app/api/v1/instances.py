"""WhatsApp instance lifecycle and settings endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_evolution_client, get_owned_instance
from app.clients.evolution import EvolutionClient
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.instance import Instance
from app.models.tenant import Tenant
from app.schemas.instance import (
    InstanceCreate,
    InstanceRead,
    InstanceSettingsUpdate,
    PresenceUpdate,
)

router = APIRouter(prefix="/instances", tags=["Instances"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_instance(
    body: InstanceCreate,
    tenant: Tenant = Depends(get_current_tenant),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a WhatsApp instance in Evolution API and bind it to the current tenant."""
    existing = (
        await db.execute(select(Instance).where(Instance.instance_name == body.instance_name))
    ).scalar_one_or_none()
    if existing:
        raise AppError(
            f"Instância '{body.instance_name}' já está cadastrada.",
            status.HTTP_409_CONFLICT,
        )

    evo_payload: dict[str, Any] = {
        "instanceName": body.instance_name,
        "qrcode": body.qrcode,
        "integration": body.integration,
        "rejectCall": body.reject_call,
        "groupsIgnore": body.groups_ignore,
        "alwaysOnline": body.always_online,
        "readMessages": body.read_messages,
        "readStatus": body.read_status,
    }
    if body.number:
        evo_payload["number"] = body.number

    evo_resp = await evo.instances.create(evo_payload)
    evo_instance_id = None
    if isinstance(evo_resp, dict):
        inst_data = evo_resp.get("instance")
        if isinstance(inst_data, dict):
            evo_instance_id = inst_data.get("instanceId")

    instance = Instance(
        tenant_id=tenant.id,
        instance_name=body.instance_name,
        evo_instance_id=evo_instance_id,
        status="created",
        webhook_url=body.webhook_url,
        webhook_secret=body.webhook_secret,
        webhook_events=body.webhook_events,
        ai_enabled=body.ai_enabled,
        ai_model=body.ai_model,
        ai_system_prompt=body.ai_system_prompt,
    )
    db.add(instance)
    await db.flush()
    await db.refresh(instance)

    return {
        "instance": InstanceRead.model_validate(instance).model_dump(mode="json"),
        "evolution": evo_resp,
    }


@router.get("", response_model=list[InstanceRead])
async def list_instances(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[Instance]:
    """List instances owned by the authenticated tenant (all if admin)."""
    stmt = select(Instance).order_by(Instance.created_at.desc())
    if not tenant.is_admin:
        stmt = stmt.where(Instance.tenant_id == tenant.id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{instance_name}/connect")
async def connect_instance(
    number: str | None = Query(default=None, description="Número para gerar pairing code"),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Connect an instance and return QR Code / pairing code."""
    return await evo.instances.connect(instance.instance_name, number=number)


@router.get("/{instance_name}/status")
async def instance_status(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Check the connection state of an instance."""
    return await evo.instances.connection_state(instance.instance_name)


@router.post("/{instance_name}/restart")
async def restart_instance(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Restart an instance in Evolution API."""
    return await evo.instances.restart(instance.instance_name)


@router.delete("/{instance_name}/logout")
async def logout_instance(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Disconnect WhatsApp session from an instance."""
    resp = await evo.instances.logout(instance.instance_name)
    instance.status = "close"
    await db.flush()
    return resp


@router.delete("/{instance_name}")
async def delete_instance(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete an instance from Evolution API and local database."""
    resp = await evo.instances.delete(instance.instance_name)
    await db.delete(instance)
    await db.flush()
    return resp


@router.post("/{instance_name}/presence")
async def set_instance_presence(
    body: PresenceUpdate,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Set global presence (available / unavailable) for an instance."""
    return await evo.instances.set_presence(instance.instance_name, body.presence)


@router.get("/{instance_name}/settings")
async def get_instance_settings(
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Get behavior settings for an instance."""
    return await evo.instances.get_settings(instance.instance_name)


@router.post("/{instance_name}/settings")
async def update_instance_settings(
    body: InstanceSettingsUpdate,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Update behavior settings for an instance."""
    return await evo.instances.set_settings(instance.instance_name, body.model_dump())
