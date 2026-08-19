"""Async ClickUp REST client."""
from __future__ import annotations

from typing import Any
import aiohttp

from homeassistant.util import dt as dt_util

from .const import API_BASE


class ClickUpError(Exception):
    """Base API error."""


class InvalidAuth(ClickUpError):
    """Authorization error (invalid API key)."""


class InvalidTeam(ClickUpError):
    """Team access error (invalid Team ID)."""


class InvalidWorkspaceAccess(ClickUpError):
    """Workspace is not authorized for the API key."""


class ClickUpClient:
    """Thin wrapper around the ClickUp API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, team_id: str) -> None:
        self._session = session
        self._headers = {"Authorization": api_key, "Content-Type": "application/json"}
        self._team_id = team_id
        self._hierarchy_cache: dict[str, str] = {}

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

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Generic method to execute requests to the ClickUp API."""
        async with self._session.request(
            method, f"{API_BASE}{path}", headers=self._headers, **kwargs
        ) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise ClickUpError(f"ClickUp API Error {resp.status}: {text}")
            
            if resp.content_type == "application/json":
                return await resp.json()
            return None

    async def async_build_hierarchy_cache(self) -> None:
        """Fetch and cache the workspace structure (Spaces -> Folders -> Lists)."""
        self._hierarchy_cache.clear()
        
        spaces_data = await self._request("GET", f"/team/{self._team_id}/space")
        if not spaces_data:
            return

        for space in spaces_data.get("spaces", []):
            space_name = space.get("name", "Unknown Space")
            space_id = space.get("id")
            
            folders_data = await self._request("GET", f"/space/{space_id}/folder")
            if folders_data:
                for folder in folders_data.get("folders", []):
                    folder_name = folder.get("name", "Unknown Folder")
                    folder_id = folder.get("id")
                    
                    lists_data = await self._request("GET", f"/folder/{folder_id}/list")
                    if lists_data:
                        for lst in lists_data.get("lists", []):
                            self._hierarchy_cache[lst["id"]] = f"{space_name} > {folder_name} > {lst.get('name', 'Unknown List')}"
            
            folderless_lists_data = await self._request("GET", f"/space/{space_id}/list")
            if folderless_lists_data:
                for lst in folderless_lists_data.get("lists", []):
                    self._hierarchy_cache[lst["id"]] = f"{space_name} > {lst.get('name', 'Unknown List')}"

    def _summarize(self, task: dict[str, Any]) -> dict[str, Any]:
        """Keeps only the most necessary fields for the LLM to save tokens."""
        list_data = task.get("list") or {}
        list_id = list_data.get("id")
        
        location = self._hierarchy_cache.get(list_id, list_data.get("name", "Unknown"))

        due_date_raw = task.get("due_date")
        due_date_str = None
        if due_date_raw:
            try:
                dt_utc = dt_util.utc_from_timestamp(int(due_date_raw) / 1000)
                due_date_str = dt_util.as_local(dt_utc).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                due_date_str = due_date_raw

        return {
            "id": task.get("id"),
            "name": task.get("name"),
            "status": (task.get("status") or {}).get("status"),
            "due_date": due_date_str,
            "priority": (task.get("priority") or {}).get("priority"),
            "location": location,
        }

    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get the list of tasks from the workspace with hierarchical context."""
        if not self._hierarchy_cache:
            await self.async_build_hierarchy_cache()

        data = await self._request("GET", f"/team/{self._team_id}/task?subtasks=true")
        tasks = data.get("tasks", []) if data else []
        
        return [self._summarize(t) for t in tasks]