"""Prompt builders for the ClickUp Assistant LLM tools."""

from __future__ import annotations


def _build_core_instructions() -> str:
    """Build core ClickUp instructions."""
    return """=== CLICKUP INSTRUCTIONS ===
Use clickup_* tools to manage ClickUp tasks.
Task search works via string matching.
If you are unsure about an exact task name, project, or to-do,
call clickup_find_tasks without a search_query first to inspect
available options.
Never invent ClickUp tasks or task data."""


def _build_formatting_instructions() -> str:
    """Build response formatting instructions."""
    return """=== FORMATTING RULES ===
If a task has a 'parent' field, you MUST visually group or indent it
as a subtask under its parent task in your final response."""


def _build_language_instructions(
    clickup_lang: str,
    conversation_lang: str,
    translate_task_names: bool,
) -> str:
    """Build language-related instructions."""
    if clickup_lang == conversation_lang:
        return """=== LANGUAGE RULES ===
The ClickUp workspace language and conversation language are the same.
No translation is required when communicating with ClickUp tools or
when presenting task data to the user."""

    rules = [
        "=== LANGUAGE RULES ===",
        f"ClickUp workspace language: '{clickup_lang}'.",
        f"Conversation language: '{conversation_lang}'.",
        (
            "1. You MUST translate the user's search request into "
            f"'{clickup_lang}' BEFORE passing it to ClickUp tools."
        ),
    ]

    if translate_task_names:
        rules.extend(
            [
                (
                    "2. When responding to the user, translate the task's "
                    f"'name' field into '{conversation_lang}'."
                ),
                (
                    "3. The task's 'location', 'list', and 'status' fields "
                    "MUST NOT be translated. Keep them EXACTLY as returned "
                    "by ClickUp."
                ),
            ]
        )
    else:
        rules.append(
            "2. Keep task names exactly as returned by ClickUp."
        )

    return "\n".join(rules)


def build_clickup_prompt(
    clickup_lang: str,
    conversation_lang: str,
    translate_task_names: bool,
) -> str:
    """Build the complete prompt for ClickUp LLM tools."""
    sections = [
        _build_core_instructions(),
        _build_formatting_instructions(),
        _build_language_instructions(
            clickup_lang=clickup_lang,
            conversation_lang=conversation_lang,
            translate_task_names=translate_task_names,
        ),
    ]
    return "\n\n".join(sections)