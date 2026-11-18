"""Schemas for tenant and API key management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    is_admin: bool = False


class TenantRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    expires_at: datetime | None = None


class ApiKeyCreated(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    raw_key: str
    expires_at: datetime | None
    created_at: datetime


class ApiKeyRead(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
