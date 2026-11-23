"""Sensor and setup tests."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.puregym_attendance.api import (
    gym_display_name,
    parse_attendance,
)
from custom_components.puregym_attendance.const import API_URL, AUTH_URL

from .conftest import MEMBER


async def test_sensors(hass: HomeAssistant, mock_puregym, config_entry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    people = hass.states.get("sensor.puregym_andover_people_in_gym")
    assert people.state == "37"
    assert people.attributes["unit_of_measurement"] == "people"
    assert people.attributes["gym_id"] == 42
    assert people.attributes["capped"] is False
    assert hass.states.get("sensor.puregym_andover_people_in_classes").state == "4"
    assert hass.states.get("sensor.puregym_andover_capacity_used").state == "37.0"
    assert (
        hass.states.get("sensor.puregym_andover_last_refreshed").state
        == "2026-11-23T18:30:00+00:00"
    )
    # Off by default.
    assert hass.states.get("sensor.puregym_andover_maximum_capacity") is None

    # Asked for the home gym.
    gym_call = next(c for c in mock_puregym.mock_calls if "gymSessions" in str(c[1]))
    assert gym_call[1].query["gymId"] == "42"

    assert await hass.config_entries.async_unload(config_entry.entry_id)


async def test_bad_login_starts_reauth(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    aioclient_mock.post(AUTH_URL, status=400)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_api_down_retries(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    aioclient_mock.post(AUTH_URL, json={"access_token": "tok", "expires_in": 3600})
    aioclient_mock.get(f"{API_URL}/api/v2/member", json=MEMBER)
    aioclient_mock.get(f"{API_URL}/api/v2/gymSessions/gym", status=500)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


def test_parse_attendance() -> None:
    a = parse_attendance(
        {"TotalPeopleInGym": "100", "TotalPeopleSuffix": "+", "MaximumCapacity": 0}
    )
    assert a.people == 100
    assert a.people_capped is True
    assert a.max_capacity is None
    assert a.percent_full is None
    assert parse_attendance({}).people is None


def test_gym_display_name() -> None:
    assert gym_display_name("PureGym Andover") == "Andover"
    assert gym_display_name("Pure Gym London Bank") == "London Bank"
    assert gym_display_name("Andover") == "Andover"
