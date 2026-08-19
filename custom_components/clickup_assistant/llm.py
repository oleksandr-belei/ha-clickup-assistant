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


_PROMPT_TEMPLATE = """Use clickup_* tools to manage ClickUp tasks.
Task search works via string matching. If unsure about exact names, call clickup_find_tasks without a query first to see available options.
{language_directives}"""


class ClickUpFindTasksTool(llm.Tool):
    name = "clickup_find_tasks"
    description = "Tool to find tasks, projects, to-dos, or chores in ClickUp."
    
    def __init__(self, clickup_lang: str) -> None:
        """Initialize the tool."""
        self.parameters = vol.Schema(
            {
                vol.Optional(
                    "search_query",
                    description=f"Optional. Query string translated into the workspace language ({clickup_lang}).",
                ): str
            }
        )

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

                matches = process.extract(
                    search_query,
                    search_dict,
                    scorer=fuzz.token_set_ratio,
                    processor=utils.default_process,
                    limit=15,
                    score_cutoff=60,
                )

                filtered_tasks = [tasks[match[2]] for match in matches]
                return {
                    "tasks": filtered_tasks,
                    "note": f"Filtered by query: {search_query}"
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
    
    clickup_lang = options.get("clickup_language", "en")
    translate_task_names = options.get("translate_task_names", True)
    
    language_directives = ""
    
    # Build strict rules only if translation is needed
    if clickup_lang != llm_context.language:
        rules = [
            f"Workspace language is '{clickup_lang}', conversation is in '{llm_context.language}'.",
            f"1. You MUST translate user queries into '{clickup_lang}' BEFORE passing them to tools."
        ]
        
        if translate_task_names:
            rules.append(f"2. When responding, the task's 'name' field MUST be translated into '{llm_context.language}'.")
            rules.append("3. The task's 'location', 'list', and 'status' fields MUST NOT be translated. Keep them EXACTLY as returned.")
        
        # Format as a highly visible block for the LLM
        language_directives = "\n\n=== STRICT LANGUAGE RULES ===\n" + "\n".join(rules)

    prompt = _PROMPT_TEMPLATE.format(language_directives=language_directives)

    return LLMTools(
        tools=[ClickUpFindTasksTool(clickup_lang=clickup_lang)],
        prompt=prompt,
    )