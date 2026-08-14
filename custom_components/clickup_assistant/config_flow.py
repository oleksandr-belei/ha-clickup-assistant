"""Config flow for ClickUp Assistant."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ClickUpClient,
    ClickUpError,
    InvalidAuth,
    InvalidTeam,
    InvalidWorkspaceAccess,
)

from .const import CONF_API_KEY, CONF_TEAM_ID, DOMAIN

# Використовуємо TextSelector для приховування пароля (зірочки)
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_TEAM_ID): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
    }
)

class ClickUpAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ClickUp Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            client = ClickUpClient(
                session=async_get_clientsession(self.hass),
                api_key=user_input[CONF_API_KEY],
                team_id=user_input[CONF_TEAM_ID],
            )
            
            try:
                await client.async_validate()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidTeam:
                errors["base"] = "invalid_team"
            except InvalidWorkspaceAccess:
                errors["base"] = "workspace_not_authorized"
            except ClickUpError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_TEAM_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"ClickUp Workspace ({user_input[CONF_TEAM_ID]})",
                    data=user_input,
                )

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)