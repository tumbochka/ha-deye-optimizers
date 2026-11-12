"""Connectivity sensors for optimizers and concentrators."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeyeConfigEntry
from .entity import ConcentratorEntity, OptimizerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: DeyeConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up online sensors."""
    coordinator = entry.runtime_data
    known_opt: set[str] = set()
    known_conc: set[str] = set()

    def add_new() -> None:
        entities: list[BinarySensorEntity] = []
        for serial in coordinator.data.concentrators:
            if serial not in known_conc:
                known_conc.add(serial)
                entities.append(ConcentratorOnline(coordinator, serial, "online"))
        for serial in coordinator.data.optimizers:
            if serial not in known_opt:
                known_opt.add(serial)
                entities.append(OptimizerOnline(coordinator, serial, "online"))
        if entities:
            async_add_entities(entities)

    add_new()
    entry.async_on_unload(coordinator.async_add_listener(add_new))


class OptimizerOnline(OptimizerEntity, BinarySensorEntity):
    """Whether the cloud reports the optimizer as online."""

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        opt = self.optimizer
        return opt.online if opt else None


class ConcentratorOnline(ConcentratorEntity, BinarySensorEntity):
    """Whether the cloud reports the concentrator as online."""

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        conc = self.concentrator
        return conc.online if conc else None
