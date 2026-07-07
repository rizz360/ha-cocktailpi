"""Common fixtures for the CocktailPi tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Prevent the real setup from running when a config entry is created."""
    with patch("custom_components.cocktailpi.async_setup_entry", return_value=True) as mock_setup:
        yield mock_setup
