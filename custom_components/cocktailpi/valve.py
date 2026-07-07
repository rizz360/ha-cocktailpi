"""Valve platform for CocktailPi pump control: open = running, closed = stopped.

Pumps don't report an "is running" flag over REST (only via the WebSocket
``pump/runningstate`` topic - see documentation/API.md), so each pump valve
is optimistic about its own state immediately after a command, then
corrected by the coordinator's WS overlay once a runningstate message
arrives. The "all pumps" valve has no per-aggregate WS topic, so it always
reports its state optimistically (assumed_state).
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CocktailPiError
from .const import DATA_PUMP_RUNNING, DATA_PUMPS, PUMP_RUNNING_STATES
from .coordinator import CocktailPiConfigEntry, CocktailPiCoordinator
from .device import hub_device_info, pump_label


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CocktailPiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CocktailPi valves from a config entry."""
    coordinator = entry.runtime_data

    entities: list[ValveEntity] = [CocktailPiAllPumpsValve(coordinator, entry)]
    for pump_id in coordinator.data[DATA_PUMPS]:
        entities.append(CocktailPiPumpValve(coordinator, entry, pump_id))

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("pump_up", {}, "async_pump_up")
    platform.async_register_entity_service("pump_back", {}, "async_pump_back")


class CocktailPiPumpValve(CoordinatorEntity[CocktailPiCoordinator], ValveEntity):
    """A single pump: open = running, closed = stopped."""

    _attr_has_entity_name = True
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False
    _attr_icon = "mdi:pump"

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry, pump_id: int) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._pump_id = pump_id
        self._attr_unique_id = f"{entry.entry_id}_pump_{pump_id}_valve"
        self._optimistic_open: bool | None = None

    @property
    def _pump(self) -> dict[str, Any] | None:
        return self.coordinator.data[DATA_PUMPS].get(self._pump_id)

    @property
    def available(self) -> bool:
        return super().available and self._pump is not None

    @property
    def device_info(self) -> DeviceInfo:
        return hub_device_info(self._entry, None)

    @property
    def name(self) -> str:
        pump = self._pump
        return pump_label(pump) if pump else f"Pump {self._pump_id}"

    @property
    def assumed_state(self) -> bool:
        # Once we've received at least one WS runningstate message for this
        # pump, we have authoritative state and don't need to assume.
        return self._pump_id not in self.coordinator.data[DATA_PUMP_RUNNING]

    @property
    def is_closed(self) -> bool | None:
        pump_running = self.coordinator.data[DATA_PUMP_RUNNING]
        if self._pump_id in pump_running:
            running = pump_running[self._pump_id]
            state = (running.get("runningState") or {}).get("state") if running else None
            return state not in PUMP_RUNNING_STATES
        if self._optimistic_open is None:
            return None
        return not self._optimistic_open

    async def async_open_valve(self) -> None:
        self._optimistic_open = True
        self.async_write_ha_state()
        try:
            await self.coordinator.api.async_start_pump(self._pump_id)
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not start pump: {err}") from err

    async def async_close_valve(self) -> None:
        self._optimistic_open = False
        self.async_write_ha_state()
        try:
            await self.coordinator.api.async_stop_pump(self._pump_id)
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not stop pump: {err}") from err

    async def async_pump_up(self) -> None:
        """Prime the tube (run forward)."""
        try:
            await self.coordinator.api.async_pump_up(self._pump_id)
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not prime pump: {err}") from err

    async def async_pump_back(self) -> None:
        """Empty the tube back into the bottle (run reverse; requires direction-control hardware)."""
        try:
            await self.coordinator.api.async_pump_back(self._pump_id)
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not reverse-prime pump: {err}") from err


class CocktailPiAllPumpsValve(CoordinatorEntity[CocktailPiCoordinator], ValveEntity):
    """A single valve that starts/stops every pump at once."""

    _attr_has_entity_name = True
    _attr_name = "All pumps"
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False
    _attr_assumed_state = True
    _attr_icon = "mdi:pump"

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_all_pumps_valve"
        self._is_closed = True

    @property
    def device_info(self) -> DeviceInfo:
        return hub_device_info(self._entry, None)

    @property
    def is_closed(self) -> bool:
        return self._is_closed

    async def async_open_valve(self) -> None:
        self._is_closed = False
        self.async_write_ha_state()
        try:
            await self.coordinator.api.async_start_pump()
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not start pumps: {err}") from err

    async def async_close_valve(self) -> None:
        self._is_closed = True
        self.async_write_ha_state()
        try:
            await self.coordinator.api.async_stop_pump()
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not stop pumps: {err}") from err

    async def async_pump_up(self) -> None:
        raise HomeAssistantError("pump_up targets a single pump valve, not the all-pumps valve")

    async def async_pump_back(self) -> None:
        raise HomeAssistantError("pump_back targets a single pump valve, not the all-pumps valve")
