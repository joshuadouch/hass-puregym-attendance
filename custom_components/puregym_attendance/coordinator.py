"""Polls PureGym for the home gym's attendance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Attendance, Member, PureGymAuthError, PureGymClient, PureGymError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The home gym rarely changes, so only re-read the member this often.
MEMBER_REFRESH = timedelta(hours=6)

type PureGymConfigEntry = ConfigEntry[PureGymCoordinator]


@dataclass(slots=True)
class PureGymData:
    """What the sensors read."""

    member: Member
    attendance: Attendance


class PureGymCoordinator(DataUpdateCoordinator[PureGymData]):
    """Fetches attendance for the member's home gym."""

    config_entry: PureGymConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PureGymConfigEntry, client: PureGymClient
    ) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL)
        interval = timedelta(minutes=minutes) if minutes else DEFAULT_SCAN_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=interval,
        )
        self.client = client
        self._member: Member | None = None
        self._member_read = dt_util.utcnow()

    async def _async_update_data(self) -> PureGymData:
        try:
            now = dt_util.utcnow()
            if self._member is None or now - self._member_read > MEMBER_REFRESH:
                self._member = await self.client.get_member()
                self._member_read = now
            if self._member.home_gym is None:
                raise UpdateFailed("This PureGym account has no home gym")
            attendance = await self.client.get_attendance(self._member.home_gym.id)
        except PureGymAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PureGymError as err:
            raise UpdateFailed(str(err)) from err
        return PureGymData(member=self._member, attendance=attendance)
