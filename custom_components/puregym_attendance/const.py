"""Constants for the PureGym Attendance integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "puregym_attendance"

AUTH_URL = "https://auth.puregym.com/connect/token"
API_URL = "https://capi.puregym.com"
# The members' app API only answers requests that look like the app.
USER_AGENT = "PureGym/1523 CFNetwork/1312 Darwin/21.0.0"
CLIENT_ID = "ro.client"
SCOPE = "pgcapi"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
MIN_SCAN_INTERVAL_MINUTES = 1
MAX_SCAN_INTERVAL_MINUTES = 60
