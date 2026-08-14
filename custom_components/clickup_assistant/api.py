"""Async ClickUp REST client."""
from __future__ import annotations

import aiohttp

from .const import API_BASE

class ClickUpError(Exception):
    """Базова помилка API."""

class ClickUpClient:
    """Тонка обгортка над ClickUp API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, team_id: str) -> None:
        self._session = session
        self._headers = {"Authorization": api_key, "Content-Type": "application/json"}
        self._team_id = team_id

    async def async_validate(self) -> None:
        """Перевірка креденшлів (робимо запит до інфо про команду)."""
        async with self._session.get(
            f"{API_BASE}/team/{self._team_id}", headers=self._headers
        ) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise ClickUpError(f"ClickUp API Error {resp.status}: {text}")