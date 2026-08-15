"""Expose ClickUp task management as tools for the built-in Assist LLM API."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.llm import LLMContext, ToolInput
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN


class ClickUpFindTasksTool(llm.Tool):
    name = "clickup_find_tasks"
    parameters = vol.Schema({})

    def __init__(
        self,
        options: dict,
        response_language: str,
    ) -> None:
        """Initialize the tool with dynamic instructions based on options."""
        clickup_lang = options.get("clickup_language", "en")
        translate_task_names = options.get("translate_task_names", False)

        description = (
            "Get a list of current tasks from ClickUp."
            f"\nIMPORTANT: Translate search arguments to this language: {clickup_lang}."
        )

        if translate_task_names:
            description += (
                f"\nIMPORTANT: The user's current language is {response_language}."
                "\nWhen presenting the task list to the user, you MUST translate "
                "EVERY task name from the original ClickUp language into the "
                f"user's current language ({response_language}). "
                "Do not copy the original task name when a translation is possible. "
                "Preserve the meaning of the original task name."
            )
        else:
            description += (
                "\nIMPORTANT: Preserve every task name exactly as returned by "
                "ClickUp. Do not translate task names."
            )

        self.description = description

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> JsonObjectType:
        # Get the first configured workspace
        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            raise HomeAssistantError("ClickUp Assistant is not configured")

        # Take the first available workspace
        entry_data = next(iter(hass.data[DOMAIN].values()))
        client = entry_data["client"]

        try:
            tasks = await client.get_tasks()
            return {"tasks": tasks}
        except Exception as err:
            raise HomeAssistantError(f"ClickUp API error: {err}") from err


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: LLMContext, api_id: str
) -> LLMTools | None:
    """Register tools in Assist."""
    if DOMAIN not in hass.data or api_id != "assist":
        return None

    # Retrieve options from the configuration entry
    entries = hass.config_entries.async_entries(DOMAIN)
    options = entries[0].options if entries else {}

    return LLMTools(
        tools=[
            ClickUpFindTasksTool(
                options,
                response_language=llm_context.language,
            )
        ],
    )