"""Facade aggregating all Evolution API v2 domain clients."""

import httpx

from app.clients.evolution.base import EvolutionBaseClient
from app.clients.evolution.chats import ChatsClient
from app.clients.evolution.groups import GroupsClient
from app.clients.evolution.instances import InstancesClient
from app.clients.evolution.integrations import IntegrationsClient
from app.clients.evolution.messages import MessagesClient
from app.clients.evolution.webhooks import WebhooksClient


class EvolutionClient:
    """High-level async facade over all Evolution API v2 endpoints."""

    def __init__(self, http_client: httpx.AsyncClient, base_url: str, api_key: str) -> None:
        self._base = EvolutionBaseClient(
            http_client=http_client, base_url=base_url, api_key=api_key
        )
        self.instances = InstancesClient(self._base)
        self.messages = MessagesClient(self._base)
        self.chats = ChatsClient(self._base)
        self.groups = GroupsClient(self._base)
        self.webhooks = WebhooksClient(self._base)
        self.integrations = IntegrationsClient(self._base)
