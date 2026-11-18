"""Evolution API native integrations endpoints (Typebot, Chatwoot, OpenAI, Dify)."""

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends

from app.api.deps import get_evolution_client, get_owned_instance
from app.clients.evolution import EvolutionClient
from app.models.instance import Instance

IntegrationName = Literal["typebot", "chatwoot", "openai", "dify"]

router = APIRouter(prefix="/integrations/{instance_name}", tags=["Integrations"])


@router.post("/{integration}")
async def set_integration(
    integration: IntegrationName,
    payload: dict[str, Any] = Body(...),
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Create or update an Evolution API integration for the instance."""
    return await evo.integrations.configure(integration, instance.instance_name, payload)


@router.get("/{integration}")
async def get_integration(
    integration: IntegrationName,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Fetch integration settings for the instance."""
    return await evo.integrations.find(integration, instance.instance_name)


@router.delete("/{integration}/{integration_id}")
async def delete_integration(
    integration: IntegrationName,
    integration_id: str,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
) -> Any:
    """Delete an integration from the instance."""
    return await evo.integrations.delete(integration, instance.instance_name, integration_id)
