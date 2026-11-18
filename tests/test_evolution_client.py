"""Unit tests for EvolutionClient using respx HTTP mocking."""

import httpx
import pytest
import respx

from app.clients.evolution import EvolutionClient
from app.core.exceptions import EvolutionAPIError


@respx.mock
async def test_evolution_client_send_text_and_instances() -> None:
    base_url = "http://evolution.test"
    respx.post(f"{base_url}/message/sendText/minha-instancia").mock(
        return_value=httpx.Response(201, json={"key": {"id": "msg-1"}})
    )
    respx.get(f"{base_url}/instance/connectionState/minha-instancia").mock(
        return_value=httpx.Response(200, json={"instance": {"state": "open"}})
    )

    async with httpx.AsyncClient() as http_client:
        client = EvolutionClient(http_client=http_client, base_url=base_url, api_key="evo-key")
        msg_resp = await client.messages.send_text(
            "minha-instancia", {"number": "5511999999999", "text": "Olá"}
        )
        state_resp = await client.instances.connection_state("minha-instancia")

    assert msg_resp["key"]["id"] == "msg-1"
    assert state_resp["instance"]["state"] == "open"


@respx.mock
async def test_evolution_client_raises_on_upstream_error() -> None:
    base_url = "http://evolution.test"
    respx.get(f"{base_url}/instance/connectionState/inexistente").mock(
        return_value=httpx.Response(404, json={"message": "Instance not found"})
    )

    async with httpx.AsyncClient() as http_client:
        client = EvolutionClient(http_client=http_client, base_url=base_url, api_key="evo-key")
        with pytest.raises(EvolutionAPIError) as exc_info:
            await client.instances.connection_state("inexistente")

    assert exc_info.value.status_code == 404
