"""Small async client for the PureGym members' app API.

Login is the member's email and PIN (the same as the PureGym app). The API
hands back a bearer token, which we keep until it runs out or a request
answers 401, then log in again.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
import time
from typing import Any

import aiohttp

from .const import API_URL, AUTH_URL, CLIENT_ID, SCOPE, USER_AGENT

TIMEOUT = aiohttp.ClientTimeout(total=15)


class PureGymError(Exception):
    """PureGym could not be reached or answered with an error."""


class PureGymAuthError(PureGymError):
    """The email or PIN was refused."""


@dataclass(slots=True)
class Gym:
    """A PureGym gym."""

    id: int
    name: str


@dataclass(slots=True)
class Member:
    """The logged-in member."""

    id: str
    first_name: str | None
    home_gym: Gym | None


@dataclass(slots=True)
class Attendance:
    """How busy a gym is right now."""

    people: int | None
    people_capped: bool
    people_in_classes: int | None
    max_capacity: int | None
    last_refreshed: str | None
    raw: dict[str, Any]

    @property
    def percent_full(self) -> float | None:
        """People as a share of capacity, when PureGym gives a capacity."""
        if self.people is None or not self.max_capacity:
            return None
        return round(100 * self.people / self.max_capacity, 1)


def _num(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None


def gym_display_name(name: str) -> str:
    """'PureGym Andover' -> 'Andover'."""
    return re.sub(r"^\s*pure\s*gym\s*", "", name, flags=re.IGNORECASE).strip() or name


def parse_attendance(data: dict[str, Any]) -> Attendance:
    """Turn a gymSessions/gym answer into an Attendance."""
    return Attendance(
        people=_num(data.get("TotalPeopleInGym")),
        people_capped=bool(data.get("TotalPeopleSuffix")),
        people_in_classes=_num(data.get("TotalPeopleInClasses")),
        max_capacity=_num(data.get("MaximumCapacity")) or None,
        last_refreshed=data.get("LastRefreshed") or data.get("AttendanceTime"),
        raw=data,
    )


class PureGymClient:
    """Talks to the PureGym members' app API."""

    def __init__(self, session: aiohttp.ClientSession, email: str, pin: str) -> None:
        self._session = session
        self._email = email
        self._pin = pin
        self._token: str | None = None
        self._token_expires = 0.0
        self._lock = asyncio.Lock()

    async def _login(self) -> None:
        form = {
            "grant_type": "password",
            "username": self._email,
            "password": self._pin,
            "scope": SCOPE,
            "client_id": CLIENT_ID,
        }
        try:
            async with self._session.post(
                AUTH_URL,
                data=form,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise PureGymAuthError(f"login refused ({resp.status})")
                if resp.status != 200:
                    raise PureGymError(f"login failed ({resp.status})")
                body = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PureGymError(f"login failed: {err}") from err

        token = body.get("access_token") if isinstance(body, dict) else None
        if not token:
            raise PureGymAuthError("login gave no token")
        self._token = token
        life = int(body.get("expires_in") or 3600)
        self._token_expires = time.monotonic() + max(60, life - 120)

    async def _ensure_token(self) -> str:
        async with self._lock:
            if self._token is None or time.monotonic() >= self._token_expires:
                await self._login()
            assert self._token is not None
            return self._token

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        for attempt in range(2):
            token = await self._ensure_token()
            try:
                async with self._session.get(
                    f"{API_URL}{path}",
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                    },
                    timeout=TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        # Token was revoked early; log in again and retry once.
                        self._token = None
                        continue
                    if resp.status == 401:
                        raise PureGymAuthError("token refused")
                    if resp.status != 200:
                        raise PureGymError(f"{path} answered {resp.status}")
                    return await resp.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError) as err:
                raise PureGymError(f"{path} failed: {err}") from err
        raise PureGymError(f"{path} failed")

    async def get_member(self) -> Member:
        """The logged-in member and their home gym."""
        data = await self._get("/api/v2/member")
        if not isinstance(data, dict):
            raise PureGymError("unexpected member answer")
        home = data.get("HomeGym") or {}
        gym = None
        if home.get("Id") is not None:
            gym = Gym(id=int(home["Id"]), name=home.get("Name") or f"Gym {home['Id']}")
        member_id = (
            data.get("Id") or data.get("MemberId") or data.get("Email") or self._email
        )
        return Member(id=str(member_id), first_name=data.get("FirstName"), home_gym=gym)

    async def get_attendance(self, gym_id: int) -> Attendance:
        """How busy a gym is right now."""
        data = await self._get("/api/v2/gymSessions/gym", {"gymId": gym_id})
        if not isinstance(data, dict):
            raise PureGymError("unexpected attendance answer")
        return parse_attendance(data)
