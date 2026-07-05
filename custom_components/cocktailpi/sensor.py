"""Sensor platform for CocktailPi: pump fill level/status, and current cocktail."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COCKTAIL, DATA_PUMPS, DATA_VERSION, DOMAIN
from .coordinator import CocktailPiCoordinator
from .device import hub_device_info, pump_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up CocktailPi sensors from a config entry."""
    coordinator: CocktailPiCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [CocktailPiCurrentCocktailSensor(coordinator, entry)]
    for pump_id in coordinator.data[DATA_PUMPS]:
        entities.append(CocktailPiPumpFillLevelSensor(coordinator, entry, pump_id))
        entities.append(CocktailPiPumpStatusSensor(coordinator, entry, pump_id))

    async_add_entities(entities)


class CocktailPiCurrentCocktailSensor(CoordinatorEntity[CocktailPiCoordinator], SensorEntity):
    """Name of the cocktail currently being produced, regardless of who ordered it."""

    _attr_has_entity_name = True
    _attr_name = "Current cocktail"
    _attr_icon = "mdi:glass-cocktail"

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_current_cocktail"

    @property
    def device_info(self) -> DeviceInfo:
        return hub_device_info(self._entry, self.coordinator.data.get(DATA_VERSION))

    @property
    def native_value(self) -> str | None:
        progress = self.coordinator.data.get(DATA_COCKTAIL)
        if not progress:
            return None
        recipe = progress.get("recipe") or {}
        return recipe.get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        progress = self.coordinator.data.get(DATA_COCKTAIL)
        if not progress:
            return {}
        return {
            "state": progress.get("state"),
            "progress": progress.get("progress"),
            "written_instruction": progress.get("writtenInstruction"),
        }


class _PumpEntityBase(CoordinatorEntity[CocktailPiCoordinator]):
    """Shared lookup/availability logic for entities tied to one pump."""

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry, pump_id: int) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._pump_id = pump_id

    @property
    def _pump(self) -> dict[str, Any] | None:
        return self.coordinator.data[DATA_PUMPS].get(self._pump_id)

    @property
    def available(self) -> bool:
        return super().available and self._pump is not None

    @property
    def device_info(self) -> DeviceInfo | None:
        pump = self._pump
        return pump_device_info(self._entry, pump) if pump else None


class CocktailPiPumpFillLevelSensor(_PumpEntityBase, SensorEntity):
    """A pump's reservoir fill level, in mL."""

    _attr_has_entity_name = True
    _attr_name = "Fill level"
    _attr_native_unit_of_measurement = "mL"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cup-water"

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry, pump_id: int) -> None:
        super().__init__(coordinator, entry, pump_id)
        self._attr_unique_id = f"{entry.entry_id}_pump_{pump_id}_fill_level"

    @property
    def native_value(self) -> int | None:
        pump = self._pump
        return pump.get("fillingLevelInMl") if pump else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pump = self._pump
        return {"tube_capacity_ml": pump.get("tubeCapacityInMl")} if pump else {}


class CocktailPiPumpStatusSensor(_PumpEntityBase, SensorEntity):
    """A pump's currently assigned ingredient and readiness state."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry, pump_id: int) -> None:
        super().__init__(coordinator, entry, pump_id)
        self._attr_unique_id = f"{entry.entry_id}_pump_{pump_id}_status"

    @property
    def native_value(self) -> str | None:
        pump = self._pump
        if not pump:
            return None
        ingredient = pump.get("currentIngredient")
        return ingredient["name"] if ingredient else "Empty"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pump = self._pump
        if not pump:
            return {}
        return {
            "pump_state": pump.get("state"),
            "pumped_up": pump.get("pumpedUp"),
            "power_consumption": pump.get("powerConsumption"),
            "type": pump.get("type"),
        }
