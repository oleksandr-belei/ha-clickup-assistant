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
    description = "Отримати список поточних задач з ClickUp."
    # Поки що не приймаємо жодних аргументів, просто тягнемо всі задачі
    parameters = vol.Schema({})

    async def async_call(
        self, hass: HomeAssistant, tool_input: ToolInput, llm_context: LLMContext
    ) -> JsonObjectType:
        # Беремо перший налаштований workspace
        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            raise HomeAssistantError("ClickUp Assistant не налаштовано")
        
        # Оскільки в майбутньому може бути кілька воркспейсів, беремо перший доступний
        entry_data = next(iter(hass.data[DOMAIN].values()))
        client = entry_data["client"]
        
        try:
            tasks = await client.get_tasks()
            return {"tasks": tasks}
        except Exception as err:
            raise HomeAssistantError(f"Помилка ClickUp API: {err}") from err


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: LLMContext, api_id: str
) -> LLMTools | None:
    """Реєстрація інструментів в Assist."""
    if DOMAIN not in hass.data or api_id != "assist":
        return None

    return LLMTools(tools=[ClickUpFindTasksTool()])