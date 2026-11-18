"""Schemas for Google Gemini Interactions API and WhatsApp conversational memory."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]


class GeminiGenerateRequest(BaseModel):
    input: str | list[dict[str, Any]] | None = None
    prompt: str | None = Field(default=None, min_length=1)
    system_instruction: str | None = None
    model: str | None = None
    previous_interaction_id: str | None = None
    thinking_level: ThinkingLevel | None = None
    generation_config: dict[str, Any] | None = None
    store: bool = True

    @model_validator(mode="after")
    def validate_input_or_prompt(self) -> "GeminiGenerateRequest":
        if not self.input and not self.prompt:
            raise ValueError("Informe 'input' ou 'prompt'.")
        return self


class GeminiGenerateResponse(BaseModel):
    id: str | None = None
    previous_interaction_id: str | None = None
    model: str
    status: str = "completed"
    text: str
    raw: dict[str, Any]


class GeminiWhatsAppReplyRequest(BaseModel):
    number: str = Field(..., description="Número com DDI+DDD ou JID")
    prompt: str = Field(..., min_length=1)
    system_instruction: str | None = None
    model: str | None = None
    thinking_level: ThinkingLevel | None = None
    use_memory: bool = True
    reset_memory: bool = False
    delay: int | None = Field(default=None, ge=0)


class InstanceAIConfigUpdate(BaseModel):
    ai_enabled: bool
    ai_model: str | None = "gemini-4-hydrogen"
    ai_system_prompt: str | None = Field(default=None, max_length=2000)
