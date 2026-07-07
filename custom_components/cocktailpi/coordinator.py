"""Data update coordinator for CocktailPi.

Baseline state (pump list, fill levels, etc.) is fetched via REST polling on
a normal interval, since that's simple and robust. On top of that, a single
WebSocket connection (see ws.py) is opened once the first REST poll
succeeds, subscribing to the few live-push topics that have no REST
equivalent - most importantly "what cocktail is currently being made", which
CocktailPi only ever pushes, regardless of whether the order was placed from
Home Assistant, the touchscreen, or anywhere else.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CocktailPiApiClient, CocktailPiAuthError, CocktailPiConnectionError, CocktailPiError
from .const import (
    DATA_COCKTAIL,
    DATA_DISPENSING_AREA,
    DATA_GPIO_HEALTHY,
    DATA_PUMP_RUNNING,
    DATA_PUMPS,
    DATA_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .ws import CocktailPiWebSocketClient

_LOGGER = logging.getLogger(__name__)


class CocktailPiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates REST-polled pump/system state plus WS-pushed live state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: CocktailPiApiClient) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL)
        self.api = api
        self.entry = entry
        self.ws: CocktailPiWebSocketClient | None = None
        self.data: dict[str, Any] = {
            DATA_PUMPS: {},
            DATA_COCKTAIL: None,
            DATA_PUMP_RUNNING: {},
            DATA_VERSION: None,
            DATA_DISPENSING_AREA: None,
            DATA_GPIO_HEALTHY: None,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            pumps = await self.api.async_get_pumps()
        except CocktailPiAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication with CocktailPi failed: {err}") from err
        except (CocktailPiConnectionError, CocktailPiError) as err:
            raise UpdateFailed(f"Error communicating with CocktailPi: {err}") from err

        self.data[DATA_PUMPS] = {pump["id"]: pump for pump in pumps}

        if self.data.get(DATA_VERSION) is None:
            self.data[DATA_VERSION] = await self.api.async_get_version()

        await self._async_update_gpio_health()

        self._ensure_websocket()
        return self.data

    async def _async_update_gpio_health(self) -> None:
        """Refresh GPIO/I2C board health, in isolation from the rest of the update.

        GET /api/gpio/ requires SUPER_ADMIN (see documentation/API.md), which
        most CocktailPi accounts won't have - that's expected and shouldn't
        fail the whole coordinator update, so failures just leave the health
        state unknown (None) rather than raising UpdateFailed.
        """
        try:
            boards = await self.api.async_get_gpio_boards()
        except CocktailPiError as err:
            _LOGGER.debug("Could not fetch GPIO board status: %s", err)
            self.data[DATA_GPIO_HEALTHY] = None
            return
        self.data[DATA_GPIO_HEALTHY] = not any(board.get("errors") for board in boards)

    def _ensure_websocket(self) -> None:
        """Start the WS overlay once, using the pump ids known at that point.

        Pumps are essentially static hardware, so pumps added after startup
        won't get a live running-state subscription until HA is reloaded -
        an acceptable v1 limitation.
        """
        if self.ws is not None:
            return

        self.ws = CocktailPiWebSocketClient(self.api.session, self.api.base_url, lambda: self.api.token)
        self.ws.subscribe("/user/topic/cocktailprogress", self._on_cocktail_progress)
        self.ws.subscribe("/user/topic/pump/layout", self._on_pump_layout)
        self.ws.subscribe("/user/topic/dispensingarea", self._on_dispensing_area)
        for pump_id in self.data[DATA_PUMPS]:
            self.ws.subscribe(
                f"/user/topic/pump/runningstate/{pump_id}",
                lambda payload, pid=pump_id: self._on_pump_running_state(pid, payload),
            )
        self.ws.async_start()

    def _on_cocktail_progress(self, payload: Any) -> None:
        self.data[DATA_COCKTAIL] = None if payload == "DELETE" else payload
        self.async_set_updated_data(self.data)

    def _on_pump_layout(self, payload: Any) -> None:
        if isinstance(payload, list):
            self.data[DATA_PUMPS] = {pump["id"]: pump for pump in payload}
            self.async_set_updated_data(self.data)

    def _on_pump_running_state(self, pump_id: int, payload: Any) -> None:
        self.data[DATA_PUMP_RUNNING][pump_id] = None if payload == "DELETE" else payload
        self.async_set_updated_data(self.data)

    def _on_dispensing_area(self, payload: Any) -> None:
        self.data[DATA_DISPENSING_AREA] = None if payload == "DELETE" else payload
        self.async_set_updated_data(self.data)

    async def async_shutdown_ws(self) -> None:
        """Stop the WebSocket client, e.g. on config entry unload."""
        if self.ws is not None:
            await self.ws.async_stop()
            self.ws = None


CocktailPiConfigEntry = ConfigEntry[CocktailPiCoordinator]
