"""Base entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Concentrator, DeyeOptimizersCoordinator, Optimizer


class OptimizerEntity(CoordinatorEntity[DeyeOptimizersCoordinator]):
    """Entity bound to one optimizer."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DeyeOptimizersCoordinator, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self.serial = serial
        self._attr_unique_id = f"{serial}_{key}"
        opt = coordinator.data.optimizers[serial]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=f"Deye optimizer {serial}",
            manufacturer="Deye",
            model="Panel optimizer",
            model_id=opt.product_id,
            serial_number=serial,
            suggested_area=None,
            via_device=(DOMAIN, opt.concentrator_serial) if opt.concentrator_serial else None,
        )

    @property
    def optimizer(self) -> Optimizer | None:
        return self.coordinator.data.optimizers.get(self.serial)

    @property
    def available(self) -> bool:
        return super().available and self.optimizer is not None


class ConcentratorEntity(CoordinatorEntity[DeyeOptimizersCoordinator]):
    """Entity bound to one optimizer concentrator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DeyeOptimizersCoordinator, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self.serial = serial
        self._attr_unique_id = f"concentrator_{serial}_{key}"
        conc = coordinator.data.concentrators[serial]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=f"Deye optimizer concentrator {serial}",
            manufacturer="Deye",
            model="Optimizer concentrator",
            model_id=conc.product_id,
            serial_number=serial,
        )

    @property
    def concentrator(self) -> Concentrator | None:
        return self.coordinator.data.concentrators.get(self.serial)

    @property
    def available(self) -> bool:
        return super().available and self.concentrator is not None
