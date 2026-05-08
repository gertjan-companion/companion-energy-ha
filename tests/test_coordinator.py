"""Tests for Companion Energy coordinators."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.companion_energy.api_client import (
    CompanionEnergyApiError,
    CompanionEnergyAuthError,
)
from custom_components.companion_energy.coordinator import (
    CompanionEnergyAssetCoordinator,
)

from .conftest import (
    ASSET_UUID,
    CUSTOMER_ID,
    CUSTOMER_NAME,
)


@pytest.fixture
def hass():
    h = MagicMock()
    h.loop = MagicMock()
    return h


async def test_asset_coordinator_happy_path(hass, mock_api_client):
    coordinator = CompanionEnergyAssetCoordinator(
        hass, mock_api_client, CUSTOMER_ID, CUSTOMER_NAME
    )
    data = await coordinator._async_update_data()

    assert data["customer_id"] == CUSTOMER_ID
    assert data["customer_name"] == CUSTOMER_NAME
    assert len(data["assets"]) == 1
    assert data["assets"][0]["uuid"] == ASSET_UUID
    assert data["setpoints"][ASSET_UUID]["steering_state"] == "discharge"
    assert data["setpoints"][ASSET_UUID]["power_kw"] == -10.5


async def test_asset_coordinator_auth_error(hass, mock_api_client):
    mock_api_client.get_assets.side_effect = CompanionEnergyAuthError("401")
    coordinator = CompanionEnergyAssetCoordinator(
        hass, mock_api_client, CUSTOMER_ID, CUSTOMER_NAME
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_asset_coordinator_api_error(hass, mock_api_client):
    mock_api_client.get_assets.side_effect = CompanionEnergyApiError("timeout")
    coordinator = CompanionEnergyAssetCoordinator(
        hass, mock_api_client, CUSTOMER_ID, CUSTOMER_NAME
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_asset_coordinator_setpoint_none_uses_unsteered(hass, mock_api_client):
    mock_api_client.get_asset_setpoint.return_value = None
    coordinator = CompanionEnergyAssetCoordinator(
        hass, mock_api_client, CUSTOMER_ID, CUSTOMER_NAME
    )
    data = await coordinator._async_update_data()
    assert data["setpoints"][ASSET_UUID]["steering_state"] == "unsteered"
    assert data["setpoints"][ASSET_UUID]["power_kw"] is None


async def test_asset_coordinator_preserves_last_soc(hass, mock_api_client):
    coordinator = CompanionEnergyAssetCoordinator(
        hass, mock_api_client, CUSTOMER_ID, CUSTOMER_NAME
    )
    # Simulate existing SOC data
    coordinator.data = {"last_soc": {ASSET_UUID: 0.72}}
    data = await coordinator._async_update_data()
    assert data["last_soc"][ASSET_UUID] == 0.72
