"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1 import ai, auth, backups, chats, groups, instances, integrations, messages, webhooks

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(messages.router)
api_router.include_router(chats.router)
api_router.include_router(groups.router)
api_router.include_router(webhooks.router)
api_router.include_router(integrations.router)
api_router.include_router(ai.router)
api_router.include_router(backups.router)
