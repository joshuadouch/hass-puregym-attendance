"""Diagnostics for PureGym Attendance."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PIN
from homeassistant.core import HomeAssistant

from .coordinator import PureGymConfigEntry

TO_REDACT = {CONF_EMAIL, CONF_PIN, "id", "first_name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PureGymConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics."""
    data = entry.runtime_data.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "member": async_redact_data(asdict(data.member), TO_REDACT) if data else None,
        "attendance": data.attendance.raw if data else None,
    }
