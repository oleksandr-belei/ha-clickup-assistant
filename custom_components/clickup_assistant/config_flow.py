"""Config flow for ClickUp Assistant."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    LanguageSelector,
    LanguageSelectorConfig,
)

from .api import (
    ClickUpClient,
    ClickUpError,
    InvalidAuth,
    InvalidTeam,
    InvalidWorkspaceAccess,
)
from .const import CONF_API_KEY, CONF_TEAM_ID, DOMAIN

# Use TextSelector to hide the password
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


class ClickUpOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        schema_dict = {
            vol.Required(
                "clickup_language",
                default=options.get("clickup_language", "en"),
            ): LanguageSelector(LanguageSelectorConfig()),
            vol.Required(
                "translate_task_names",
                default=options.get("translate_task_names", True),
            ): selector.BooleanSelector(),
        }

        data_schema = vol.Schema(schema_dict)

        return self.async_show_form(step_id="init", data_schema=data_schema)


class ClickUpAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle options flow for ClickUp Assistant."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
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

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ClickUpOptionsFlowHandler()