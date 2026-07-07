"""Shared device-info helpers, used by both the sensor and valve platforms."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def hub_device_info(entry: ConfigEntry, version: str | None) -> DeviceInfo:
    """Device info for the CocktailPi machine/hub itself."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="CocktailPi",
        manufacturer="CocktailPi",
        sw_version=version,
    )


def pump_label(pump: dict[str, Any]) -> str:
    """Human-readable label for a pump, used to prefix its entity names.

    All pump entities live on the single CocktailPi hub device (rather than
    one sub-device per pump), so this label is what disambiguates e.g.
    "Pump 1 Fill level" from "Pump 2 Fill level" in the entity list.
    """
    return pump.get("name") or pump.get("printName") or f"Pump {pump['id']}"
