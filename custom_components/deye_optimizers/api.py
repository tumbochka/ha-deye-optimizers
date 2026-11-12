"""Minimal async client for the (undocumented) deyecloud.com web API.

The official Deye Cloud OpenAPI does not expose per-optimizer data, so this
client talks to the same endpoints the deyecloud.com web app uses.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterator
from typing import Any

import aiohttp

from .const import BASE_URL, CLIENT_ID

TOKEN_PATH = "/oauth-s/oauth/token"
REFRESH_MARGIN = 3 * 86400  # refresh when less than 3 days of validity remain
TIMEOUT = aiohttp.ClientTimeout(total=30)
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "platform": "Web",
    "system": "Deye",
    "language": "en",
    "origin": BASE_URL,
    "referer": BASE_URL + "/",
}


class DeyeCloudError(Exception):
    """Generic API error."""


class DeyeCloudAuthError(DeyeCloudError):
    """Credentials rejected."""


def hash_password(password: str) -> str:
    """Return the sha256 hex digest deyecloud.com expects instead of the password."""
    return hashlib.sha256(password.encode()).hexdigest()


def _identity_type(username: str) -> str:
    if "@" in username:
        return "2"  # e-mail
    if username.lstrip("+").isdigit():
        return "1"  # mobile phone
    return "3"  # plain user name


class DeyeCloudClient:
    """deyecloud.com client with automatic login / token refresh."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password_hash: str,
        data_center: str,
        token: dict[str, Any] | None = None,
        on_token: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._session = session
        self._username = username
        self._password_hash = password_hash
        self._data_center = data_center
        self._token = token
        self._on_token = on_token

    # ---------------------------------------------------------------- auth
    async def _token_request(self, form: dict[str, str]) -> dict[str, Any]:
        try:
            async with self._session.post(
                BASE_URL + TOKEN_PATH,
                data=form,
                headers={**HEADERS, "content-type": "application/x-www-form-urlencoded"},
                timeout=TIMEOUT,
            ) as resp:
                try:
                    body = await resp.json(content_type=None)
                except ValueError:
                    body = {}
                if resp.status == 200 and isinstance(body, dict) and body.get("access_token"):
                    return body
                msg = (body or {}).get("error_description") or (body or {}).get("msg") or f"HTTP {resp.status}"
                if resp.status in (400, 401, 403):
                    raise DeyeCloudAuthError(msg)
                raise DeyeCloudError(msg)
        except aiohttp.ClientError as err:
            raise DeyeCloudError(str(err)) from err

    def _store(self, body: dict[str, Any]) -> None:
        self._token = {
            "access": body["access_token"],
            "refresh": body.get("refresh_token"),
            "exp": time.time() + int(body.get("expires_in", 86400)),
        }
        if self._on_token:
            self._on_token(self._token)

    async def login(self) -> None:
        """Log in with user name + password hash, then switch to the data center."""
        first = await self._token_request(
            {
                "grant_type": "password",
                "identity_type": _identity_type(self._username),
                "username": self._username,
                "client_id": CLIENT_ID,
                "org_id": "0",
                "record_flag": "0",
                "system": "Deye",
                "lang": "en",
                "password": self._password_hash,
            }
        )
        second = await self._token_request(
            {
                "grant_type": "switch_org",
                "access_token": first["access_token"],
                "client_id": CLIENT_ID,
                "org_id": "0",
                "data_center": self._data_center,
                "lang": "en",
            }
        )
        self._store(second)

    async def _refresh(self) -> None:
        refresh = (self._token or {}).get("refresh")
        if refresh:
            try:
                self._store(
                    await self._token_request(
                        {"grant_type": "refresh_token", "client_id": CLIENT_ID, "refresh_token": refresh}
                    )
                )
                return
            except DeyeCloudError:
                pass
        await self.login()

    async def _ensure_token(self) -> None:
        if not self._token:
            await self.login()
        elif self._token["exp"] - time.time() < REFRESH_MARGIN:
            await self._refresh()

    # ------------------------------------------------------------- requests
    async def _request(self, method: str, path: str, json: Any = None) -> Any:
        await self._ensure_token()
        for attempt in range(2):
            assert self._token
            try:
                async with self._session.request(
                    method,
                    BASE_URL + path,
                    json=json,
                    headers={**HEADERS, "authorization": "Bearer " + self._token["access"]},
                    timeout=TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        await self._refresh()
                        continue
                    if resp.status == 401:
                        raise DeyeCloudAuthError("token rejected")
                    if resp.status >= 400:
                        raise DeyeCloudError(f"{path}: HTTP {resp.status}")
                    return await resp.json(content_type=None)
            except aiohttp.ClientError as err:
                raise DeyeCloudError(str(err)) from err
        raise DeyeCloudError(f"{path}: retry failed")

    async def stations(self) -> list[dict[str, Any]]:
        """Return the stations (plants) of the account."""
        body = await self._request(
            "POST", "/maintain-s/operating/station/v2/search?page=1&size=100", json={"station": {}}
        )
        return [item["station"] for item in (body or {}).get("data") or [] if item.get("station")]

    async def devices(self, station_id: int) -> dict[str, Any]:
        """Return the device tree of a station (collectors with their children)."""
        return await self._request("GET", f"/maintain-s/power/deye/device/{station_id}/all-device") or {}

    async def day_history(self, device_id: int, day: str) -> list[dict[str, Any]]:
        """Return today's ~5 min history of a device. day = 'YYYY/MM/DD'."""
        return (
            await self._request(
                "GET", f"/device-s/device/{device_id}/stats/day?day={day.replace('/', '%2F')}&lan=en"
            )
            or []
        )


def walk_devices(tree: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield every device in an all-device tree."""
    stack = list(tree.get("devices") or [])
    while stack:
        dev = stack.pop()
        yield dev
        stack.extend(dev.get("childs") or [])


def latest_values(history: list[dict[str, Any]]) -> dict[str, tuple[float, int]]:
    """Map storageName -> (latest value, collectionTime) of a day history."""
    out: dict[str, tuple[float, int]] = {}
    for field in history or []:
        points = field.get("detailList") or []
        if not points:
            continue
        last = max(points, key=lambda p: p.get("collectionTime") or 0)
        try:
            out[field["storageName"]] = (float(last["value"]), int(last["collectionTime"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out
