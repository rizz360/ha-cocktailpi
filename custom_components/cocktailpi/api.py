"""Thin async REST client for the CocktailPi backend.

Endpoint shapes and quirks (trailing-slash requirements, auth flow, response
envelopes) are documented in ``documentation/API.md`` at the root of the
CocktailPi repository this integration was built alongside - re-check that
file if the backend's API ever changes.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError

_LOGGER = logging.getLogger(__name__)


class CocktailPiError(Exception):
    """Base error for anything that goes wrong talking to CocktailPi."""


class CocktailPiAuthError(CocktailPiError):
    """Raised when login fails (bad credentials) or a token can't be refreshed."""


class CocktailPiConnectionError(CocktailPiError):
    """Raised when the CocktailPi host can't be reached at all."""


class CocktailPiApiClient:
    """Wraps the CocktailPi REST API with JWT bearer authentication."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = False,
    ) -> None:
        self._session = session
        scheme = "https" if use_ssl else "http"
        self._base_url = f"{scheme}://{host}:{port}"
        self._username = username
        self._password = password
        self._token: str | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def token(self) -> str | None:
        return self._token

    async def async_login(self) -> str:
        """Log in and cache the bearer token (requested with remember=True, ~10y lifetime)."""
        try:
            async with self._session.post(
                f"{self._base_url}/api/auth/login",
                json={
                    "username": self._username,
                    "password": self._password,
                    "remember": True,
                },
            ) as resp:
                if resp.status == 401:
                    raise CocktailPiAuthError("Invalid username or password")
                try:
                    resp.raise_for_status()
                except ClientResponseError as err:
                    raise CocktailPiError(f"Login failed: HTTP {resp.status}") from err
                data = await resp.json(content_type=None)
        except ClientError as err:
            raise CocktailPiConnectionError(str(err)) from err

        self._token = data["accessToken"]
        return self._token

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        _retry_on_401: bool = True,
        **kwargs: Any,
    ) -> Any:
        if self._token is None:
            await self.async_login()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"

        try:
            resp = await self._session.request(
                method, f"{self._base_url}{path}", headers=headers, **kwargs
            )
        except ClientError as err:
            raise CocktailPiConnectionError(str(err)) from err

        async with resp:
            if resp.status == 401 and _retry_on_401:
                await self.async_login()
                return await self._request_json(method, path, _retry_on_401=False, **kwargs)
            if resp.status == 404:
                return None
            try:
                resp.raise_for_status()
            except ClientResponseError as err:
                raise CocktailPiError(f"{method} {path} failed: HTTP {resp.status}") from err
            if resp.content_length == 0:
                return None
            return await resp.json(content_type=None)

    # --- Pumps ---------------------------------------------------------

    async def async_get_pumps(self) -> list[dict[str, Any]]:
        """GET /api/pump/ - list all configured pumps."""
        return await self._request_json("GET", "/api/pump/") or []

    async def async_start_pump(self, pump_id: int | None = None) -> None:
        """PUT /api/pump/start - start one pump, or all pumps if pump_id is None."""
        params = {"id": pump_id} if pump_id is not None else {}
        await self._request_json("PUT", "/api/pump/start", params=params)

    async def async_stop_pump(self, pump_id: int | None = None) -> None:
        """PUT /api/pump/stop - stop one pump, or all pumps if pump_id is None."""
        params = {"id": pump_id} if pump_id is not None else {}
        await self._request_json("PUT", "/api/pump/stop", params=params)

    async def async_pump_up(self, pump_id: int) -> None:
        """PUT /api/pump/{id}/pumpup - prime the tube (pump forward)."""
        await self._request_json("PUT", f"/api/pump/{pump_id}/pumpup")

    async def async_pump_back(self, pump_id: int) -> None:
        """PUT /api/pump/{id}/pumpback - empty the tube back (pump reverse)."""
        await self._request_json("PUT", f"/api/pump/{pump_id}/pumpback")

    # --- Cocktails -------------------------------------------------------

    async def async_order_cocktail(
        self,
        recipe_id: int,
        amount_ml: int | None = None,
        is_ingredient: bool = False,
    ) -> None:
        """PUT /api/cocktail/{recipeId} - start producing a recipe."""
        body = {
            "amountOrderedInMl": amount_ml,
            "ingredientGroupReplacements": [],
            "customisations": {"boost": 0, "additionalIngredients": []},
        }
        await self._request_json(
            "PUT",
            f"/api/cocktail/{recipe_id}",
            params={"isIngredient": str(is_ingredient).lower()},
            json=body,
        )

    async def async_cancel_cocktail(self) -> None:
        """DELETE /api/cocktail/ - cancel the cocktail currently in production."""
        await self._request_json("DELETE", "/api/cocktail/")

    # --- Recipes ---------------------------------------------------------

    async def async_get_recipes(self, search_name: str | None = None) -> list[dict[str, Any]]:
        """GET /api/recipe/ - search recipes by name, returns the page's content list."""
        params = {"searchName": search_name} if search_name else {}
        page = await self._request_json("GET", "/api/recipe/", params=params)
        return (page or {}).get("content", [])

    async def async_find_recipe_id(self, name: str) -> int:
        """Resolve a recipe name to its id via GET /api/recipe/?searchName=... .

        Prefers an exact case-insensitive name match; otherwise falls back to
        the first search result.
        """
        recipes = await self.async_get_recipes(search_name=name)
        if not recipes:
            raise CocktailPiError(f"No recipe found matching '{name}'")
        for recipe in recipes:
            if recipe.get("name", "").casefold() == name.casefold():
                return recipe["id"]
        return recipes[0]["id"]

    # --- GPIO --------------------------------------------------------------

    async def async_get_gpio_boards(self) -> list[dict[str, Any]]:
        """GET /api/gpio/ - list configured GPIO/I2C boards, each with its current errors.

        Requires SUPER_ADMIN; callers should expect a CocktailPiError (HTTP
        403) on accounts without that role.
        """
        return await self._request_json("GET", "/api/gpio/") or []

    # --- System ----------------------------------------------------------

    async def async_get_version(self) -> str | None:
        """GET /api/system/version - public endpoint, no auth required."""
        try:
            async with self._session.get(f"{self._base_url}/api/system/version") as resp:
                if resp.status != 200:
                    return None
                return await resp.json(content_type=None)
        except ClientError:
            return None
