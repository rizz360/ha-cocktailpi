"""Constants for the CocktailPi integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "cocktailpi"

CONF_USE_SSL = "use_ssl"

DEFAULT_PORT = 80
DEFAULT_USE_SSL = False

# REST poll interval (seconds), user-tunable via the options flow.
DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 10
MAX_SCAN_INTERVAL_SECONDS = 300

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.VALVE,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
]

# Keys inside the coordinator's .data dict.
DATA_PUMPS = "pumps"
DATA_COCKTAIL = "cocktail"
DATA_PUMP_RUNNING = "pump_running"
DATA_VERSION = "version"
DATA_DISPENSING_AREA = "dispensing_area"
DATA_GPIO_HEALTHY = "gpio_healthy"

# Service names.
SERVICE_ORDER_COCKTAIL = "order_cocktail"
SERVICE_CANCEL_COCKTAIL = "cancel_cocktail"

# Service field names.
ATTR_RECIPE_ID = "recipe_id"
ATTR_RECIPE_NAME = "recipe_name"
ATTR_AMOUNT_ML = "amount_ml"
ATTR_IS_INGREDIENT = "is_ingredient"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"

# PumpTask.State values (backend/model/pump/motortasks/PumpTask.java) that mean "actively pumping".
PUMP_RUNNING_STATES = {"RUNNING"}
