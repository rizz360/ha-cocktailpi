"""Tests for the CocktailPi REST API client."""

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.cocktailpi.api import (
    CocktailPiApiClient,
    CocktailPiAuthError,
    CocktailPiConnectionError,
    CocktailPiError,
)

BASE = "http://1.2.3.4:80"
LOGIN_URL = f"{BASE}/api/auth/login"


def _client(hass: HomeAssistant) -> CocktailPiApiClient:
    return CocktailPiApiClient(async_get_clientsession(hass), "1.2.3.4", 80, "admin", "secret")


async def test_login_success(hass: HomeAssistant, aioclient_mock) -> None:
    """A successful login stores and returns the bearer token."""
    aioclient_mock.post(LOGIN_URL, json={"accessToken": "tok"})
    client = _client(hass)

    assert await client.async_login() == "tok"
    assert client.token == "tok"
    assert aioclient_mock.mock_calls[0][2]["remember"] is True


async def test_login_invalid_credentials(hass: HomeAssistant, aioclient_mock) -> None:
    """A 401 on login raises the auth error."""
    aioclient_mock.post(LOGIN_URL, status=401)

    with pytest.raises(CocktailPiAuthError):
        await _client(hass).async_login()


async def test_login_connection_error(hass: HomeAssistant, aioclient_mock) -> None:
    """A network failure on login raises the connection error."""
    aioclient_mock.post(LOGIN_URL, exc=aiohttp.ClientError("boom"))

    with pytest.raises(CocktailPiConnectionError):
        await _client(hass).async_login()


async def test_get_pumps_logs_in_and_sends_bearer(hass: HomeAssistant, aioclient_mock) -> None:
    """The first authenticated request logs in lazily and sends the token."""
    aioclient_mock.post(LOGIN_URL, json={"accessToken": "tok"})
    aioclient_mock.get(f"{BASE}/api/pump/", json=[{"id": 1, "name": "Pump 1"}])

    pumps = await _client(hass).async_get_pumps()

    assert pumps == [{"id": 1, "name": "Pump 1"}]
    headers = aioclient_mock.mock_calls[-1][3]
    assert headers["Authorization"] == "Bearer tok"


async def test_request_http_error(hass: HomeAssistant, aioclient_mock) -> None:
    """A non-401/404 HTTP error surfaces as CocktailPiError."""
    aioclient_mock.post(LOGIN_URL, json={"accessToken": "tok"})
    aioclient_mock.get(f"{BASE}/api/pump/", status=500)

    with pytest.raises(CocktailPiError):
        await _client(hass).async_get_pumps()


async def test_find_recipe_id_prefers_exact_match(hass: HomeAssistant, aioclient_mock) -> None:
    """Name resolution prefers a case-insensitive exact match over the first hit."""
    aioclient_mock.post(LOGIN_URL, json={"accessToken": "tok"})
    aioclient_mock.get(
        f"{BASE}/api/recipe/",
        json={
            "content": [
                {"id": 1, "name": "Mojito Royale"},
                {"id": 2, "name": "Mojito"},
            ]
        },
    )

    assert await _client(hass).async_find_recipe_id("mojito") == 2


async def test_find_recipe_id_no_match(hass: HomeAssistant, aioclient_mock) -> None:
    """An empty search result raises CocktailPiError."""
    aioclient_mock.post(LOGIN_URL, json={"accessToken": "tok"})
    aioclient_mock.get(f"{BASE}/api/recipe/", json={"content": []})

    with pytest.raises(CocktailPiError):
        await _client(hass).async_find_recipe_id("does not exist")
