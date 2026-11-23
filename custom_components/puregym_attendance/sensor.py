"""Sensors for PureGym Attendance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import Attendance, gym_display_name
from .const import DOMAIN
from .coordinator import PureGymConfigEntry, PureGymCoordinator

PARALLEL_UPDATES = 0

UNIT_PEOPLE = "people"


def parse_refreshed(value: str | None) -> datetime | None:
    """PureGym's refresh time; times without a zone are taken as local."""
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_utc(parsed)


@dataclass(frozen=True, kw_only=True)
class PureGymSensorDescription(SensorEntityDescription):
    """Describes a PureGym sensor."""

    value_fn: Callable[[Attendance], Any]


SENSORS: tuple[PureGymSensorDescription, ...] = (
    PureGymSensorDescription(
        key="people",
        translation_key="people",
        native_unit_of_measurement=UNIT_PEOPLE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda a: a.people,
    ),
    PureGymSensorDescription(
        key="people_in_classes",
        translation_key="people_in_classes",
        native_unit_of_measurement=UNIT_PEOPLE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda a: a.people_in_classes,
    ),
    PureGymSensorDescription(
        key="percent_full",
        translation_key="percent_full",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda a: a.percent_full,
    ),
    PureGymSensorDescription(
        key="max_capacity",
        translation_key="max_capacity",
        native_unit_of_measurement=UNIT_PEOPLE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda a: a.max_capacity,
    ),
    PureGymSensorDescription(
        key="last_refreshed",
        translation_key="last_refreshed",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda a: parse_refreshed(a.last_refreshed),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PureGymConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the sensors for the home gym."""
    coordinator = entry.runtime_data
    async_add_entities(PureGymSensor(coordinator, d) for d in SENSORS)


class PureGymSensor(CoordinatorEntity[PureGymCoordinator], SensorEntity):
    """One reading about the home gym."""

    _attr_has_entity_name = True
    _attr_attribution = "Data from PureGym"
    entity_description: PureGymSensorDescription

    def __init__(
        self, coordinator: PureGymCoordinator, description: PureGymSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        gym = coordinator.data.member.home_gym
        assert gym is not None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=f"PureGym {gym_display_name(gym.name)}",
            manufacturer="PureGym",
            model="Gym attendance",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.puregym.com/members/",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data.attendance)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "people":
            return None
        data = self.coordinator.data
        gym = data.member.home_gym
        return {
            "gym_id": gym.id if gym else None,
            "gym_name": gym.name if gym else None,
            # PureGym shows e.g. "100+" when it caps the count.
            "capped": data.attendance.people_capped,
        }
