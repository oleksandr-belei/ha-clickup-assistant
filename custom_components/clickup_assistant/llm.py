"""Expose ClickUp task management as tools for the built-in Assist LLM API."""

from __future__ import annotations

import voluptuous as vol
from rapidfuzz import fuzz, process, utils

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.llm import LLMContext, ToolInput
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN
from .prompt import build_clickup_prompt


class ClickUpFindTasksTool(llm.Tool):
    """Tool to find tasks in ClickUp."""

    name = "clickup_find_tasks"
    description = (
        "Find tasks, projects, to-dos, or chores in ClickUp. "
        "Use this tool when you need to search for existing ClickUp tasks."
    )

    def __init__(self, clickup_lang: str, entry_id: str) -> None:
        """Initialize the tool."""
        self._entry_id = entry_id
        self.parameters = vol.Schema(
            {
                vol.Optional(
                    "search_query",
                    description=(
                        "Optional search query. "
                        f"When provided, it MUST be written in the "
                        f"ClickUp workspace language ({clickup_lang}). "
                        "Omit this parameter when you need to inspect "
                        "available tasks without filtering."
                    ),
                ): str
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> JsonObjectType:
        """Find matching ClickUp tasks."""
        entry_data = hass.data.get(DOMAIN, {}).get(self._entry_id)
        if entry_data is None:
            raise HomeAssistantError(
                "ClickUp Assistant is not configured"
            )

        client = entry_data["client"]

        search_query = tool_input.tool_args.get("search_query")

        try:
            tasks = await client.get_tasks()

            if search_query:
                search_dict = {
                    idx: (
                        f"{task.get('name', '')} "
                        f"{task.get('location', '')}"
                    )
                    for idx, task in enumerate(tasks)
                }

                matches = process.extract(
                    search_query,
                    search_dict,
                    scorer=fuzz.token_set_ratio,
                    processor=utils.default_process,
                    limit=15,
                    score_cutoff=60,
                )

                filtered_tasks = [
                    tasks[match[2]]
                    for match in matches
                ]

                return {
                    "tasks": filtered_tasks,
                    "note": f"Filtered by query: {search_query}",
                }

            return {"tasks": tasks}

        except Exception as err:
            raise HomeAssistantError(
                f"ClickUp API error: {err}"
            ) from err


@callback
def async_get_tools(
    hass: HomeAssistant,
    llm_context: LLMContext,
    api_id: str,
) -> LLMTools | None:
    """Register ClickUp tools in Assist."""
    if DOMAIN not in hass.data or api_id != "assist":
        return None

    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return None

    entry = entries[0]
    options = entry.options

    clickup_lang = options.get("clickup_language", "en")
    translate_task_names = options.get(
        "translate_task_names",
        True,
    )

    prompt = build_clickup_prompt(
        clickup_lang=clickup_lang,
        conversation_lang=llm_context.language,
        translate_task_names=translate_task_names,
    )

    return LLMTools(
        tools=[
            ClickUpFindTasksTool(
                clickup_lang=clickup_lang,
                entry_id=entry.entry_id,
            ),
        ],
        prompt=prompt,
    )