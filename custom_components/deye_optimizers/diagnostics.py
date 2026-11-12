"""Diagnostics (credentials, tokens and serial numbers redacted)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD_HASH, CONF_TOKEN
from .coordinator import DeyeConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD_HASH, CONF_TOKEN, "serial", "concentrator_serial", "device_id", "station_name"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: DeyeConfigEntry) -> dict[str, Any]:
    """Return redacted diagnostics."""
    data = entry.runtime_data.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "optimizers": [async_redact_data(asdict(o), TO_REDACT) for o in data.optimizers.values()],
        "concentrators": [async_redact_data(asdict(c), TO_REDACT) for c in data.concentrators.values()],
    }
