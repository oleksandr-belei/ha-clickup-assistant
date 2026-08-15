"""Expose ClickUp task management as tools for the built-in Assist LLM API."""
from __future__ import annotations

import voluptuous as vol
from rapidfuzz import process, fuzz, utils

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.llm import LLMContext, ToolInput
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN


class ClickUpFindTasksTool(llm.Tool):
    name = "clickup_find_tasks"
    
    def __init__(
        self,
        options: dict,
        response_language: str,
    ) -> None:
        """Initialize the tool with dynamic instructions based on options."""
        clickup_lang = options.get("clickup_language", "en")
        translate_task_names = options.get("translate_task_names", True)

        # Робимо інструкцію для параметра максимально "захищеною" від інших правил
        self.parameters = vol.Schema(
            {
                vol.Optional(
                    "search_query",
                    description=f"CRITICAL: You MUST translate the user's spoken query into {clickup_lang} BEFORE passing it here. NEVER pass {response_language} in this field.",
                ): str
            }
        )

        # Розділяємо логіку на чіткі етапи для моделі
        description = (
            "Tool to find tasks, projects, to-dos, or chores in ClickUp.\n"
            "Call this tool whenever the user asks about their work, plans, or mentions specific projects/activities.\n\n"
            "=== STEP 1: INPUT RULES ===\n"
            f"The ClickUp workspace is in {clickup_lang}. If you use 'search_query', it MUST be in {clickup_lang}.\n\n"
            "=== STEP 2: OUTPUT RULES ==="
        )

        if translate_task_names:
            description += (
                "\nAfter receiving the JSON response from this tool, you MUST translate all task names and locations "
                f"into {response_language} for your final answer. Do not output the original language."
            )
        else:
            description += (
                "\nPreserve all task names and locations exactly as returned by the tool in your final answer."
            )

        self.description = description

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> JsonObjectType:
        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            raise HomeAssistantError("ClickUp Assistant is not configured")

        entry_data = next(iter(hass.data[DOMAIN].values()))
        client = entry_data["client"]

        search_query = tool_input.tool_args.get("search_query")

        try:
            tasks = await client.get_tasks()

            if search_query:
                search_dict = {
                    idx: f"{task.get('name', '')} {task.get('location', '')}"
                    for idx, task in enumerate(tasks)
                }

                # Find the best matches (60% cutoff to filter out irrelevant noise)
                matches = process.extract(
                    search_query,
                    search_dict,
                    scorer=fuzz.token_set_ratio,       # Змінили алгоритм
                    processor=utils.default_process,   # Додали нормалізацію (нижній регістр)
                    limit=15,
                    score_cutoff=60,
                )

                filtered_tasks = [tasks[match[2]] for match in matches]
                return {
                    "tasks": filtered_tasks,
                    "note": f"Filtered by query: {search_query}",
                }

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