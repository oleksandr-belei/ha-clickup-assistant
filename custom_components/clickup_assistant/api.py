"""Async ClickUp REST client."""
from __future__ import annotations

import aiohttp

from .const import API_BASE


class ClickUpError(Exception):
    """Базова помилка API."""


class InvalidAuth(ClickUpError):
    """Помилка авторизації (невалідний API ключ)."""


class InvalidTeam(ClickUpError):
    """Помилка доступу до команди (невалідний Team ID)."""


class InvalidWorkspaceAccess(ClickUpError):
    """Workspace is not authorized for the API key."""


class ClickUpClient:
    """Тонка обгортка над ClickUp API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, team_id: str) -> None:
        self._session = session
        self._headers = {"Authorization": api_key, "Content-Type": "application/json"}
        self._team_id = team_id

    async def async_validate(self) -> None:
        """Validate ClickUp credentials."""
        async with self._session.get(
            f"{API_BASE}/team/{self._team_id}",
            headers=self._headers,
        ) as resp:
            if resp.status >= 400:
                try:
                    data = await resp.json()
                    ecode = data.get("ECODE")
                    err_msg = data.get("err", "Unknown error")
                except Exception:
                    text = await resp.text()
                    raise ClickUpError(
                        f"ClickUp API Error {resp.status}: {text}"
                    )

                if ecode in ("OAUTH_019", "OAUTH_025"):
                    raise InvalidAuth("Invalid API Key")

                if ecode == "SHARD_024":
                    raise InvalidTeam("Invalid Team ID")

                if ecode == "OAUTH_192":
                    raise InvalidWorkspaceAccess("Workspace not authorized")

                raise ClickUpError(
                    f"ClickUp API {resp.status}: {err_msg}"
                )