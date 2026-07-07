"""Tests for the CocktailPi config, reauth, and options flows."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cocktailpi.api import CocktailPiAuthError, CocktailPiConnectionError
from custom_components.cocktailpi.const import CONF_USE_SSL, DOMAIN

USER_INPUT = {
    CONF_HOST: "1.2.3.4",
    CONF_PORT: 80,
    CONF_USE_SSL: False,
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "secret",
}

LOGIN = "custom_components.cocktailpi.api.CocktailPiApiClient.async_login"


async def test_user_flow_success(hass: HomeAssistant, mock_setup_entry) -> None:
    """A valid user flow creates an entry with the entered data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(LOGIN, return_value="token"):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CocktailPi (1.2.3.4)"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == "1.2.3.4:80"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_flow_invalid_auth_then_recover(hass: HomeAssistant, mock_setup_entry) -> None:
    """Bad credentials show an error; correcting them succeeds."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(LOGIN, side_effect=CocktailPiAuthError("nope")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(LOGIN, return_value="token"):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """An unreachable host shows the cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(LOGIN, side_effect=CocktailPiConnectionError("boom")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_unknown_error(hass: HomeAssistant) -> None:
    """An unexpected exception maps to the unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(LOGIN, side_effect=ValueError("surprise")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    """Configuring the same host:port twice aborts."""
    MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id="1.2.3.4:80").add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(hass: HomeAssistant, mock_setup_entry) -> None:
    """The reauth flow validates new credentials and updates the entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id="1.2.3.4:80")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(LOGIN, side_effect=CocktailPiAuthError("still wrong")):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "bad"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(LOGIN, return_value="token"):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "newpass"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "newpass"


async def test_options_flow(hass: HomeAssistant, mock_setup_entry) -> None:
    """The options flow stores the chosen poll interval."""
    entry = MockConfigEntry(domain=DOMAIN, data=USER_INPUT, unique_id="1.2.3.4:80")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 60}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 60
