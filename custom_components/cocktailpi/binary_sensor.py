"""Binary sensor platform for CocktailPi: glass detection on the dispensing area."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_DISPENSING_AREA, DATA_GPIO_HEALTHY, DATA_VERSION
from .coordinator import CocktailPiConfigEntry, CocktailPiCoordinator
from .device import hub_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CocktailPiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CocktailPi binary sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            CocktailPiGlassDetectedBinarySensor(coordinator, entry),
            CocktailPiGpioHealthBinarySensor(coordinator, entry),
        ]
    )


class CocktailPiGlassDetectedBinarySensor(
    CoordinatorEntity[CocktailPiCoordinator], BinarySensorEntity
):
    """Whether a glass is currently detected on the dispensing area.

    Only meaningful on machines with dispensing-area/glass-detection hardware
    (see ``documentation/API.md``'s "dispensingarea" WS topic) - on machines
    without it the backend still pushes state, just always reporting the area
    as empty. Disabled by default since not every setup has this hardware.
    """

    _attr_has_entity_name = True
    _attr_name = "Glass detected"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_glass_detected"

    @property
    def device_info(self) -> DeviceInfo:
        return hub_device_info(self._entry, self.coordinator.data.get(DATA_VERSION))

    @property
    def _state(self) -> dict[str, Any] | None:
        return self.coordinator.data.get(DATA_DISPENSING_AREA)

    @property
    def is_on(self) -> bool | None:
        state = self._state
        if state is None:
            return None
        return not state.get("areaEmpty", True)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._state
        glass = state.get("glass") if state else None
        return {"glass": glass.get("name")} if glass else {}


class CocktailPiGpioHealthBinarySensor(CoordinatorEntity[CocktailPiCoordinator], BinarySensorEntity):
    """Whether any configured GPIO/I2C board is currently reporting errors.

    Backed by ``GET /api/gpio/``, which requires a SUPER_ADMIN account (see
    ``documentation/API.md``) - on any other account this stays "unknown"
    rather than reporting a false problem. Disabled by default since it only
    works for SUPER_ADMIN-configured instances and most setups won't have
    GPIO/I2C boards to worry about.
    """

    _attr_has_entity_name = True
    _attr_name = "GPIO health"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_gpio_health"

    @property
    def device_info(self) -> DeviceInfo:
        return hub_device_info(self._entry, self.coordinator.data.get(DATA_VERSION))

    @property
    def is_on(self) -> bool | None:
        healthy = self.coordinator.data.get(DATA_GPIO_HEALTHY)
        if healthy is None:
            return None
        return not healthy
