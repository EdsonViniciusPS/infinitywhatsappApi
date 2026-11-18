"""Authentication, tenant onboarding, and API key management routes."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, require_admin
from app.core.database import get_db
from app.core.exceptions import AppError, NotFoundError
from app.core.security import create_access_token, generate_api_key
from app.models.tenant import ApiKey, Tenant
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    TenantCreate,
    TenantRead,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth & Tenants"])


@router.post(
    "/tenants",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_tenant(body: TenantCreate, db: AsyncSession = Depends(get_db)) -> Tenant:
    """Create a new tenant (requires X-Master-Key or admin credentials)."""
    existing = (
        await db.execute(select(Tenant).where(Tenant.email == body.email))
    ).scalar_one_or_none()
    if existing:
        raise AppError("Já existe um tenant cadastrado com este e-mail.", status.HTTP_409_CONFLICT)

    tenant = Tenant(name=body.name, email=body.email, is_admin=body.is_admin)
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


@router.get("/tenants", response_model=list[TenantRead], dependencies=[Depends(require_admin)])
async def list_tenants(db: AsyncSession = Depends(get_db)) -> list[Tenant]:
    """List all registered tenants."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())


@router.post(
    "/tenants/{tenant_id}/api-keys",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_api_key_for_tenant(
    tenant_id: uuid.UUID,
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    """Issue a new API key for a tenant. The raw key is returned only once."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise NotFoundError("Tenant não encontrado.")

    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        tenant_id=tenant.id,
        name=body.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        expires_at=body.expires_at,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_my_api_keys(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKey]:
    """List API keys belonging to the authenticated tenant."""
    stmt = select(ApiKey).where(ApiKey.tenant_id == tenant.id).order_by(ApiKey.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.post("/token", response_model=TokenResponse)
async def exchange_api_key_for_jwt(tenant: Tenant = Depends(get_current_tenant)) -> TokenResponse:
    """Exchange a valid X-API-Key for a short-lived JWT Bearer token."""
    token = create_access_token(
        subject=str(tenant.id),
        extra_claims={"is_admin": tenant.is_admin, "email": tenant.email},
    )
    return TokenResponse(access_token=token)
