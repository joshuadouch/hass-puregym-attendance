"""PureGym Attendance: how many people are in your PureGym right now."""

from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PIN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PureGymClient
from .coordinator import PureGymConfigEntry, PureGymCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PureGymConfigEntry) -> bool:
    """Set up PureGym Attendance from a config entry."""
    client = PureGymClient(
        async_get_clientsession(hass), entry.data[CONF_EMAIL], entry.data[CONF_PIN]
    )
    coordinator = PureGymCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PureGymConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: PureGymConfigEntry) -> None:
    """Reload when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)
