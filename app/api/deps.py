"""Shared FastAPI dependencies for auth, Evolution client, and instance ownership."""

import uuid
from datetime import UTC, datetime

import jwt
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.evolution import EvolutionClient
from app.clients.gemini import GeminiClient
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token, hash_api_key, verify_constant_time
from app.models.instance import Instance
from app.models.tenant import ApiKey, Tenant

bearer_scheme = HTTPBearer(auto_error=False)


def get_evolution_client(request: Request) -> EvolutionClient:
    """Return the shared EvolutionClient bound to app.state.http_client."""
    settings = get_settings()
    return EvolutionClient(
        http_client=request.app.state.http_client,
        base_url=settings.EVOLUTION_API_URL,
        api_key=settings.EVOLUTION_API_KEY,
    )


def get_gemini_client(request: Request) -> GeminiClient:
    """Return a GeminiClient bound to the shared Redis conversation memory."""
    settings = get_settings()
    return GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        default_model=settings.GEMINI_MODEL,
        redis_client=getattr(request.app.state, "redis", None),
        conversation_ttl=settings.GEMINI_CONVERSATION_TTL_SECONDS,
    )


async def get_current_tenant(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Authenticate a tenant via X-API-Key or Bearer JWT."""
    if x_api_key:
        key_hash = hash_api_key(x_api_key)
        stmt = (
            select(ApiKey, Tenant)
            .join(Tenant, ApiKey.tenant_id == Tenant.id)
            .where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise UnauthorizedError("API Key inválida ou revogada.")
        api_key, tenant = row
        if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
            raise UnauthorizedError("API Key expirada.")
        return tenant

    if bearer and bearer.credentials:
        try:
            payload = decode_access_token(bearer.credentials)
            tenant_id = uuid.UUID(str(payload["sub"]))
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise UnauthorizedError("Token JWT inválido ou expirado.") from exc

        tenant = await db.get(Tenant, tenant_id)
        if not tenant or not tenant.is_active:
            raise UnauthorizedError("Tenant inativo ou inexistente.")
        return tenant

    raise UnauthorizedError("Informe X-API-Key ou Authorization: Bearer <token>.")


async def require_admin(
    x_master_key: str | None = Header(default=None, alias="X-Master-Key"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Authorize admin actions via X-Master-Key or an admin tenant's credentials."""
    settings = get_settings()
    if x_master_key and verify_constant_time(x_master_key, settings.ADMIN_MASTER_KEY):
        return

    if x_api_key or (bearer and bearer.credentials):
        tenant = await get_current_tenant(x_api_key=x_api_key, bearer=bearer, db=db)
        if tenant.is_admin:
            return
        raise ForbiddenError("Permissão de administrador necessária.")

    raise UnauthorizedError("Credenciais de administrador ausentes ou inválidas.")


async def get_owned_instance(
    instance_name: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> Instance:
    """Ensure the requested instance exists and belongs to the current tenant (or admin)."""
    stmt = select(Instance).where(Instance.instance_name == instance_name)
    instance = (await db.execute(stmt)).scalar_one_or_none()
    if not instance:
        raise NotFoundError(f"Instância '{instance_name}' não encontrada.")
    if not tenant.is_admin and instance.tenant_id != tenant.id:
        raise ForbiddenError("Você não tem permissão para acessar esta instância.")
    return instance
