"""HTTP forwarder to an upstream System One provider."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class UpstreamError(Exception):
    def __init__(
        self,
        status_code: int,
        body: Any,
        *,
        content_type: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.content_type = content_type
        super().__init__(f"upstream returned {status_code}")


class UpstreamClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._settings.upstream_api_key:
            headers["Authorization"] = f"Bearer {self._settings.upstream_api_key}"
        self._client = httpx.AsyncClient(
            timeout=self._settings.upstream_timeout_s,
            headers=headers,
        )

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("UpstreamClient is not started")
        return self._client

    async def post_systemone(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.post(
            self._settings.systemone_url,
            json=payload,
        )
        return self._parse(response)

    async def get_models(self) -> tuple[int, Any]:
        """Return (status, body). Callers decide whether to use curated fallback."""
        response = await self.client.get(self._settings.models_url)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
        else:
            body = response.text
        return response.status_code, body

    def _parse(self, response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body: Any = response.json()
            except ValueError:
                body = {"detail": response.text}
        else:
            body = {"detail": response.text}

        if response.is_success:
            if not isinstance(body, dict):
                raise UpstreamError(
                    502,
                    {"detail": "upstream returned non-object JSON"},
                    content_type=content_type,
                )
            return body

        raise UpstreamError(
            response.status_code,
            body,
            content_type=content_type,
        )
