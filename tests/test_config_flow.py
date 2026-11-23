"""Config flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.puregym_attendance.const import (
    API_URL,
    AUTH_URL,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

LOGIN = {CONF_EMAIL: " me@example.com ", CONF_PIN: "12345678"}


async def test_user_flow(hass: HomeAssistant, mock_puregym) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PureGym Andover"
    assert result["data"] == {CONF_EMAIL: "me@example.com", CONF_PIN: "12345678"}
    assert result["result"].unique_id == "123456"
    # The login posts the app's form fields.
    form = mock_puregym.mock_calls[0][2]
    assert form["grant_type"] == "password"
    assert form["client_id"] == "ro.client"


async def test_user_flow_bad_pin(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(AUTH_URL, status=400, json={"error": "invalid_grant"})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_down(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(AUTH_URL, status=503)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_no_home_gym(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(AUTH_URL, json={"access_token": "tok", "expires_in": 3600})
    aioclient_mock.get(f"{API_URL}/api/v2/member", json={"Id": 1, "HomeGym": None})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["errors"] == {"base": "no_home_gym"}


async def test_already_configured(
    hass: HomeAssistant, mock_puregym, config_entry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, mock_puregym, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PIN: "87654321"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PIN] == "87654321"


async def test_options(hass: HomeAssistant, mock_puregym, config_entry) -> None:
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 2}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_SCAN_INTERVAL: 2}
    await hass.async_block_till_done()
    assert config_entry.runtime_data.update_interval.total_seconds() == 120
