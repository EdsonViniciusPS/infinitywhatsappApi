"""Google Gemini AI endpoints (Interactions API) and WhatsApp conversational memory."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_tenant,
    get_evolution_client,
    get_gemini_client,
    get_owned_instance,
)
from app.clients.evolution import EvolutionClient
from app.clients.gemini import GeminiClient
from app.core.database import get_db
from app.models.instance import Instance
from app.models.logs import MessageLog
from app.models.tenant import Tenant
from app.schemas.ai import (
    GeminiGenerateRequest,
    GeminiGenerateResponse,
    GeminiWhatsAppReplyRequest,
    InstanceAIConfigUpdate,
)

router = APIRouter(prefix="/ai", tags=["Gemini AI"])


@router.post("/generate", response_model=GeminiGenerateResponse)
async def generate_text(
    body: GeminiGenerateRequest,
    _tenant: Tenant = Depends(get_current_tenant),
    gemini: GeminiClient = Depends(get_gemini_client),
) -> GeminiGenerateResponse:
    """Create an interaction using Google Gemini Interactions API."""
    input_data = body.input if body.input is not None else (body.prompt or "")
    result = await gemini.create_interaction(
        input_data=input_data,
        model=body.model,
        system_instruction=body.system_instruction,
        previous_interaction_id=body.previous_interaction_id,
        thinking_level=body.thinking_level,
        generation_config=body.generation_config,
        store=body.store,
    )
    return GeminiGenerateResponse(
        id=result["id"],
        previous_interaction_id=body.previous_interaction_id,
        model=result["model"],
        status=result["status"],
        text=result["output_text"],
        raw=result["raw"],
    )


@router.post("/{instance_name}/send")
async def generate_and_send_whatsapp(
    body: GeminiWhatsAppReplyRequest,
    instance: Instance = Depends(get_owned_instance),
    evo: EvolutionClient = Depends(get_evolution_client),
    gemini: GeminiClient = Depends(get_gemini_client),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate text with Gemini Interactions API and send it via WhatsApp."""
    target_model = body.model or instance.ai_model or gemini.default_model
    system_prompt = body.system_instruction or instance.ai_system_prompt

    if body.use_memory:
        result = await gemini.chat_with_contact(
            instance_name=instance.instance_name,
            remote_jid=body.number,
            input_data=body.prompt,
            system_instruction=system_prompt,
            model=target_model,
            thinking_level=body.thinking_level,
            reset_memory=body.reset_memory,
        )
    else:
        result = await gemini.create_interaction(
            input_data=body.prompt,
            system_instruction=system_prompt,
            model=target_model,
            thinking_level=body.thinking_level,
        )

    text = result["output_text"]
    send_payload: dict[str, Any] = {"number": body.number, "text": text}
    if body.delay is not None:
        send_payload["delay"] = body.delay

    evo_resp = await evo.messages.send_text(instance.instance_name, send_payload)
    db.add(
        MessageLog(
            instance_id=instance.id,
            direction="outbound",
            remote_jid=body.number,
            message_type="ai_text",
            status="sent",
            payload_summary={
                "model": target_model,
                "interaction_id": result["id"],
                "previous_interaction_id": result.get("previous_interaction_id"),
            },
        )
    )
    return {
        "id": result["id"],
        "previous_interaction_id": result.get("previous_interaction_id"),
        "text": text,
        "evolution": evo_resp,
    }


@router.delete("/{instance_name}/memory/{number}")
async def clear_contact_memory(
    number: str,
    instance: Instance = Depends(get_owned_instance),
    gemini: GeminiClient = Depends(get_gemini_client),
) -> dict[str, Any]:
    """Clear stored Gemini conversation memory (previous_interaction_id) for a contact."""
    cleared = await gemini.clear_conversation(instance.instance_name, number)
    return {"instance_name": instance.instance_name, "number": number, "cleared": cleared}


@router.put("/{instance_name}/config")
async def configure_instance_ai(
    body: InstanceAIConfigUpdate,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Configure Gemini auto-reply settings for an instance."""
    instance.ai_enabled = body.ai_enabled
    instance.ai_model = body.ai_model
    instance.ai_system_prompt = body.ai_system_prompt
    await db.flush()
    return {
        "instance_name": instance.instance_name,
        "ai_enabled": instance.ai_enabled,
        "ai_model": instance.ai_model,
        "ai_system_prompt": instance.ai_system_prompt,
    }
