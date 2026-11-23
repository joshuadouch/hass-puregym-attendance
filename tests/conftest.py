"""Fixtures for PureGym Attendance tests."""

from __future__ import annotations

from homeassistant.const import CONF_EMAIL, CONF_PIN
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.puregym_attendance.const import API_URL, AUTH_URL, DOMAIN

MEMBER = {
    "Id": 123456,
    "FirstName": "Test",
    "HomeGym": {"Id": 42, "Name": "PureGym Andover"},
}
ATTENDANCE = {
    "TotalPeopleInGym": 37,
    "TotalPeopleInClasses": 4,
    "TotalPeopleSuffix": None,
    "MaximumCapacity": 100,
    "LastRefreshed": "2026-11-23T18:30:00Z",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components."""
    yield


@pytest.fixture
def mock_puregym(aioclient_mock):
    """A PureGym API that accepts the login."""
    aioclient_mock.post(AUTH_URL, json={"access_token": "tok", "expires_in": 3600})
    aioclient_mock.get(f"{API_URL}/api/v2/member", json=MEMBER)
    aioclient_mock.get(f"{API_URL}/api/v2/gymSessions/gym", json=ATTENDANCE)
    return aioclient_mock


@pytest.fixture
def config_entry():
    """A set-up PureGym entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="PureGym Andover",
        unique_id="123456",
        data={CONF_EMAIL: "me@example.com", CONF_PIN: "12345678"},
    )
