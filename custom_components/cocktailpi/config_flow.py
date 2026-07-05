"""Config flow for CocktailPi."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CocktailPiApiClient, CocktailPiAuthError, CocktailPiConnectionError
from .const import CONF_USE_SSL, DEFAULT_PORT, DEFAULT_USE_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class CocktailPiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CocktailPi."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = CocktailPiApiClient(
                session,
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_USE_SSL],
            )
            try:
                await api.async_login()
            except CocktailPiAuthError:
                errors["base"] = "invalid_auth"
            except CocktailPiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating the CocktailPi connection")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"CocktailPi ({user_input[CONF_HOST]})", data=user_input
                )

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)
