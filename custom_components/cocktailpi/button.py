"""Button platform for CocktailPi: cancel the cocktail currently in production."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CocktailPiError
from .const import DATA_VERSION, DOMAIN
from .coordinator import CocktailPiCoordinator
from .device import hub_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up CocktailPi buttons from a config entry."""
    coordinator: CocktailPiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CocktailPiCancelCocktailButton(coordinator, entry)])


class CocktailPiCancelCocktailButton(CoordinatorEntity[CocktailPiCoordinator], ButtonEntity):
    """Cancels whatever cocktail is currently being produced."""

    _attr_has_entity_name = True
    _attr_name = "Cancel cocktail"
    _attr_icon = "mdi:cancel"

    def __init__(self, coordinator: CocktailPiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_cancel_cocktail"

    @property
    def device_info(self) -> DeviceInfo:
        return hub_device_info(self._entry, self.coordinator.data.get(DATA_VERSION))

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.async_cancel_cocktail()
        except CocktailPiError as err:
            raise HomeAssistantError(f"Could not cancel cocktail: {err}") from err
