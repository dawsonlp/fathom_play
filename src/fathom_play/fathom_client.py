"""Fathom HTTP client. Thin httpx wrapper returning raw responses.

Raises FathomApiError on non-2xx. Returns ApiResponse on success.
"""

import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

BASE_URL = "https://api.fathom.ai/external/v1"


class FathomApiError(Exception):
    """Raised when the Fathom API returns a non-2xx response."""

    def __init__(self, status_code: int, headers: httpx.Headers, body: str):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        super().__init__(f"Fathom API error {status_code}: {body[:200]}")


@dataclass(frozen=True)
class ApiResponse:
    """Successful API response container."""

    status_code: int
    headers: httpx.Headers
    data: dict | list


def _load_api_key() -> str:
    load_dotenv(os.path.expanduser("~/.env"))
    api_key = os.getenv("FATHOM_API_KEY")
    if not api_key:
        raise ValueError("FATHOM_API_KEY not found in environment or ~/.env")
    return api_key


class FathomHttpClient:
    """Synchronous HTTP client for the Fathom API."""

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        key = api_key or _load_api_key()
        self._client = httpx.Client(
            base_url=base_url,
            headers={"x-api-key": key, "Accept": "application/json"},
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> ApiResponse:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise FathomApiError(resp.status_code, resp.headers, resp.text)
        return ApiResponse(
            status_code=resp.status_code,
            headers=resp.headers,
            data=resp.json(),
        )

    def list_meetings(self, **params) -> ApiResponse:
        """GET /meetings with optional query parameters."""
        return self._request("GET", "/meetings", params=params)

    def get_transcript(self, recording_id: int) -> ApiResponse:
        """GET /recordings/{recording_id}/transcript"""
        return self._request("GET", f"/recordings/{recording_id}/transcript")

    def get_summary(self, recording_id: int) -> ApiResponse:
        """GET /recordings/{recording_id}/summary"""
        return self._request("GET", f"/recordings/{recording_id}/summary")

    def list_teams(self, **params) -> ApiResponse:
        """GET /teams with optional query parameters."""
        return self._request("GET", "/teams", params=params)

    def list_team_members(self, **params) -> ApiResponse:
        """GET /team_members with optional query parameters."""
        return self._request("GET", "/team_members", params=params)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
