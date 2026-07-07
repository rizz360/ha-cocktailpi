"""The CocktailPi integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import (
    CocktailPiApiClient,
    CocktailPiAuthError,
    CocktailPiConnectionError,
    CocktailPiError,
)
from .const import (
    ATTR_AMOUNT_ML,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_IS_INGREDIENT,
    ATTR_RECIPE_ID,
    ATTR_RECIPE_NAME,
    CONF_USE_SSL,
    DOMAIN,
    PLATFORMS,
    SERVICE_CANCEL_COCKTAIL,
    SERVICE_ORDER_COCKTAIL,
)
from .coordinator import CocktailPiConfigEntry, CocktailPiCoordinator

_LOGGER = logging.getLogger(__name__)

ORDER_COCKTAIL_SCHEMA = vol.Schema(
    {
        vol.Exclusive(ATTR_RECIPE_ID, "recipe"): cv.positive_int,
        vol.Exclusive(ATTR_RECIPE_NAME, "recipe"): cv.string,
        vol.Optional(ATTR_AMOUNT_ML): vol.All(int, vol.Range(min=10, max=5000)),
        vol.Optional(ATTR_IS_INGREDIENT, default=False): cv.boolean,
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)

CANCEL_COCKTAIL_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})


def _get_coordinator(hass: HomeAssistant, call: ServiceCall) -> CocktailPiCoordinator:
    """Resolve which configured CocktailPi instance a domain-level service call targets."""
    entries: list[CocktailPiConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry.runtime_data
        raise HomeAssistantError(f"Unknown CocktailPi config entry '{entry_id}'")
    if not entries:
        raise HomeAssistantError("No CocktailPi instance is configured")
    if len(entries) > 1:
        raise HomeAssistantError(
            "Multiple CocktailPi instances are configured; specify config_entry_id"
        )
    return entries[0].runtime_data


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the domain-level services once, regardless of how many entries exist."""

    async def _async_order_cocktail(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        recipe_id = call.data.get(ATTR_RECIPE_ID)
        recipe_name = call.data.get(ATTR_RECIPE_NAME)
        try:
            if recipe_id is None:
                if recipe_name is None:
                    raise HomeAssistantError("Either recipe_id or recipe_name is required")
                recipe_id = await coordinator.api.async_find_recipe_id(recipe_name)
            await coordinator.api.async_order_cocktail(
                recipe_id,
                amount_ml=call.data.get(ATTR_AMOUNT_ML),
                is_ingredient=call.data.get(ATTR_IS_INGREDIENT, False),
            )
        except CocktailPiError as err:
            raise HomeAssistantError(str(err)) from err

    async def _async_cancel_cocktail(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        try:
            await coordinator.api.async_cancel_cocktail()
        except CocktailPiError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN, SERVICE_ORDER_COCKTAIL, _async_order_cocktail, schema=ORDER_COCKTAIL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL_COCKTAIL, _async_cancel_cocktail, schema=CANCEL_COCKTAIL_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CocktailPiConfigEntry) -> bool:
    """Set up CocktailPi from a config entry."""
    session = async_get_clientsession(hass)
    api = CocktailPiApiClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data.get(CONF_USE_SSL, False),
    )

    try:
        await api.async_login()
    except CocktailPiAuthError as err:
        raise ConfigEntryAuthFailed(f"Invalid credentials for CocktailPi: {err}") from err
    except CocktailPiConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect to CocktailPi: {err}") from err

    coordinator = CocktailPiCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_options_updated(hass: HomeAssistant, entry: CocktailPiConfigEntry) -> None:
    """Reload the entry so the coordinator picks up the new poll interval."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CocktailPiConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown_ws()
    return unload_ok
