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


def pump_device_info(entry: ConfigEntry, pump: dict[str, Any]) -> DeviceInfo:
    """Device info for a single pump, linked as a sub-device of the hub."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_pump_{pump['id']}")},
        name=pump.get("name") or pump.get("printName") or f"Pump {pump['id']}",
        manufacturer="CocktailPi",
        model=pump.get("type"),
        via_device=(DOMAIN, entry.entry_id),
    )
