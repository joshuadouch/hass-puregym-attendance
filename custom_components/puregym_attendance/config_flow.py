"""Config flow for PureGym Attendance."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PIN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import Member, PureGymAuthError, PureGymClient, PureGymError, gym_display_name
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

PIN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PIN): PIN_SELECTOR,
    }
)


class PureGymConfigFlow(ConfigFlow, domain=DOMAIN):
    """Log in with the PureGym app's email and PIN."""

    VERSION = 1

    async def _try_login(
        self, email: str, pin: str, errors: dict[str, str]
    ) -> Member | None:
        client = PureGymClient(async_get_clientsession(self.hass), email, pin)
        try:
            member = await client.get_member()
        except PureGymAuthError:
            errors["base"] = "invalid_auth"
        except PureGymError:
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error logging in to PureGym")
            errors["base"] = "unknown"
        else:
            if member.home_gym is None:
                errors["base"] = "no_home_gym"
                return None
            return member
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the email and PIN."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            pin = user_input[CONF_PIN].strip()
            member = await self._try_login(email, pin, errors)
            if member is not None:
                await self.async_set_unique_id(member.id)
                self._abort_if_unique_id_configured()
                assert member.home_gym is not None
                return self.async_create_entry(
                    title=f"PureGym {gym_display_name(member.home_gym.name)}",
                    data={CONF_EMAIL: email, CONF_PIN: pin},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """PureGym refused the saved login."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the PIN again."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            email = entry.data[CONF_EMAIL]
            pin = user_input[CONF_PIN].strip()
            member = await self._try_login(email, pin, errors)
            if member is not None:
                await self.async_set_unique_id(member.id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PIN: pin}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PIN): PIN_SELECTOR}),
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> PureGymOptionsFlow:
        """Options: how often to poll."""
        return PureGymOptionsFlow()


class PureGymOptionsFlow(OptionsFlow):
    """How often to ask PureGym."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the polling interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60)
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL_MINUTES,
                        max=MAX_SCAN_INTERVAL_MINUTES,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
