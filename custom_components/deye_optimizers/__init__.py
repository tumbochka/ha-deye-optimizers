"""Deye Cloud Optimizers: per-panel data of Deye SUN-XL02 optimizers from deyecloud.com."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DeyeCloudClient
from .const import CONF_DATA_CENTER, CONF_PASSWORD_HASH, CONF_TOKEN, DOMAIN
from .coordinator import DeyeConfigEntry, DeyeOptimizersCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: DeyeConfigEntry) -> bool:
    """Set up from a config entry."""

    def save_token(token: dict[str, Any]) -> None:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_TOKEN: token})

    client = DeyeCloudClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD_HASH],
        entry.data[CONF_DATA_CENTER],
        token=entry.data.get(CONF_TOKEN),
        on_token=save_token,
    )
    coordinator = DeyeOptimizersCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Concentrators first, so optimizers can reference them as via_device.
    registry = dr.async_get(hass)
    for conc in coordinator.data.concentrators.values():
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, conc.serial)},
            name=f"Deye optimizer concentrator {conc.serial}",
            manufacturer="Deye",
            model="Optimizer concentrator",
            model_id=conc.product_id,
            serial_number=conc.serial,
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DeyeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
