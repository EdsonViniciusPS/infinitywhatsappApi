"""Base HTTP client for Evolution API v2."""

from typing import Any

import httpx

from app.core.exceptions import EvolutionAPIError


class EvolutionBaseClient:
    """Shared async HTTP transport for all Evolution API domain clients."""

    def __init__(self, http_client: httpx.AsyncClient, base_url: str, api_key: str) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send an authenticated request to Evolution API and return parsed JSON."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}
        try:
            response = await self._http.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
            )
        except httpx.RequestError as exc:
            raise EvolutionAPIError(
                f"Falha de comunicação com a Evolution API: {exc}",
                status_code=502,
            ) from exc

        if response.status_code >= 400:
            try:
                details = response.json()
            except ValueError:
                details = response.text
            raise EvolutionAPIError(
                f"Evolution API retornou erro HTTP {response.status_code}.",
                status_code=response.status_code if response.status_code < 500 else 502,
                details=details,
            )

        if not response.content:
            return {"status": "ok"}
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}
