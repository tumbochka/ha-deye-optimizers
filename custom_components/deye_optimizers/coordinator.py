"""Data update coordinator for Deye Cloud Optimizers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DeyeCloudAuthError, DeyeCloudClient, DeyeCloudError, latest_values, walk_devices
from .const import DEVICE_TYPE_CONCENTRATOR, DEVICE_TYPE_OPTIMIZER, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class Concentrator:
    """An optimizer concentrator (e.g. SUN-XL20-B)."""

    serial: str
    device_id: int
    station_name: str | None
    online: bool
    product_id: str | None


@dataclass
class Optimizer:
    """A panel optimizer (e.g. SUN-XL02-B)."""

    serial: str
    device_id: int
    concentrator_serial: str | None
    station_name: str | None
    online: bool
    product_id: str | None
    power: float | None
    energy_today: float | None
    voltage: float | None = None
    current: float | None = None
    last_update: datetime | None = None
    time_zone: str | None = None


@dataclass
class DeyeData:
    """Everything one update returns."""

    optimizers: dict[str, Optimizer] = field(default_factory=dict)
    concentrators: dict[str, Concentrator] = field(default_factory=dict)


def _float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


type DeyeConfigEntry = ConfigEntry[DeyeOptimizersCoordinator]


class DeyeOptimizersCoordinator(DataUpdateCoordinator[DeyeData]):
    """Polls deyecloud.com for all optimizers of the account."""

    config_entry: DeyeConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DeyeConfigEntry, client: DeyeCloudClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> DeyeData:
        try:
            return await self._fetch()
        except DeyeCloudAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DeyeCloudError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch(self) -> DeyeData:
        data = DeyeData()
        previous = self.data.optimizers if self.data else {}
        for station in await self.client.stations():
            tree = await self.client.devices(station["id"])
            devices = list(walk_devices(tree))
            conc_by_id = {}
            for dev in devices:
                if dev.get("deviceType") == DEVICE_TYPE_CONCENTRATOR:
                    conc = Concentrator(
                        serial=str(dev["deviceSn"]),
                        device_id=dev["deviceId"],
                        station_name=station.get("name"),
                        online=dev.get("deviceStatus") == 1,
                        product_id=dev.get("productId"),
                    )
                    data.concentrators[conc.serial] = conc
                    conc_by_id[conc.device_id] = conc.serial
            for dev in devices:
                if dev.get("deviceType") != DEVICE_TYPE_OPTIMIZER:
                    continue
                ts = dev.get("collectionTime")
                opt = Optimizer(
                    serial=str(dev["deviceSn"]),
                    device_id=dev["deviceId"],
                    concentrator_serial=conc_by_id.get(dev.get("parentId")),
                    station_name=station.get("name"),
                    online=dev.get("deviceStatus") == 1,
                    product_id=dev.get("productId"),
                    power=_float(dev.get("generationPower")),
                    energy_today=_float(dev.get("generation")),
                    last_update=datetime.fromtimestamp(ts, timezone.utc) if ts else None,
                    time_zone=dev.get("timeZone") or station.get("regionTimezone"),
                )
                await self._add_history(opt, previous.get(opt.serial))
                data.optimizers[opt.serial] = opt
        return data

    async def _add_history(self, opt: Optimizer, prev: Optimizer | None) -> None:
        """Voltage / current only come from the day history endpoint."""
        try:
            tz = ZoneInfo(opt.time_zone) if opt.time_zone else dt_util.get_default_time_zone()
        except Exception:  # noqa: BLE001 - unknown zone name from the cloud
            tz = dt_util.get_default_time_zone()
        day = datetime.now(tz).strftime("%Y/%m/%d")
        try:
            values = latest_values(await self.client.day_history(opt.device_id, day))
        except DeyeCloudAuthError:
            raise
        except DeyeCloudError as err:
            _LOGGER.debug("history for %s failed: %s", opt.serial, err)
            if prev:
                opt.voltage, opt.current = prev.voltage, prev.current
            return
        opt.voltage = values.get("DV1", (None, 0))[0]
        opt.current = values.get("DC1", (None, 0))[0]
