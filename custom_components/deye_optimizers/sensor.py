"""Sensors for Deye panel optimizers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeyeConfigEntry, Optimizer
from .entity import OptimizerEntity


@dataclass(frozen=True, kw_only=True)
class OptimizerSensorDescription(SensorEntityDescription):
    """Describes an optimizer sensor."""

    value_fn: Callable[[Optimizer], Any]


SENSORS: tuple[OptimizerSensorDescription, ...] = (
    OptimizerSensorDescription(
        key="power",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda o: o.power,
    ),
    OptimizerSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda o: o.energy_today,
    ),
    OptimizerSensorDescription(
        key="voltage",
        translation_key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda o: o.voltage,
    ),
    OptimizerSensorDescription(
        key="current",
        translation_key="current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda o: o.current,
    ),
    OptimizerSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda o: o.last_update,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: DeyeConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Set up optimizer sensors; new optimizers appear without a restart."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    def add_new() -> None:
        new = [s for s in coordinator.data.optimizers if s not in known]
        known.update(new)
        async_add_entities(OptimizerSensor(coordinator, s, d) for s in new for d in SENSORS)

    add_new()
    entry.async_on_unload(coordinator.async_add_listener(add_new))


class OptimizerSensor(OptimizerEntity, SensorEntity):
    """A numeric/timestamp value of an optimizer."""

    entity_description: OptimizerSensorDescription

    def __init__(self, coordinator, serial: str, description: OptimizerSensorDescription) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        opt = self.optimizer
        return self.entity_description.value_fn(opt) if opt else None
