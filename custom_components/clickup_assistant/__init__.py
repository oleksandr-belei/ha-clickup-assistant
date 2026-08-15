"""The ClickUp Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ClickUpClient
from .const import CONF_API_KEY, CONF_TEAM_ID, DOMAIN


PLATFORMS: list[str] = []

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ClickUp Assistant from a config entry."""
    client = ClickUpClient(
        session=async_get_clientsession(hass),
        api_key=entry.data[CONF_API_KEY],
        team_id=entry.data[CONF_TEAM_ID],
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"client": client}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

# ... (async_unload_entry залишається без змін)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Видаляємо клієнт з пам'яті при видаленні інтеграції
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok