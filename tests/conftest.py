"""Shared pytest fixtures for Companion Energy tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def patch_frame_helper():
    """Suppress HA's frame-helper check that requires a live event loop.

    DataUpdateCoordinator calls frame.report_usage() when no config_entry is
    passed, which tries to access the HA ContextVar.  In unit tests we use a
    MagicMock hass, so we silence the check rather than spin up a real HA
    instance.
    """
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


CUSTOMER_ID = "cust-1234"
CUSTOMER_NAME = "Acme Corp"
ASSET_UUID = "asset-5678"
ASSET_NAME = "Main Battery"

MOCK_CUSTOMERS = [{"id": CUSTOMER_ID, "name": CUSTOMER_NAME}]

MOCK_ASSETS = [
    {
        "uuid": ASSET_UUID,
        "name": ASSET_NAME,
        "asset_type": "battery",
        "config": {"capacity_kwh": 100.0},
        "steering_enabled": True,
        "nomination_enabled": False,
    }
]

MOCK_SETPOINT = {
    "power_kw": -10.5,
    "steering_state": "discharge",
    "scheduled_setpoints": [],
}


@pytest.fixture
def mock_api_client():
    client = AsyncMock()
    client.get_customers = AsyncMock(return_value=MOCK_CUSTOMERS)
    client.get_assets = AsyncMock(return_value=MOCK_ASSETS)
    client.get_asset_setpoint = AsyncMock(return_value=MOCK_SETPOINT)
    client.submit_telemetry = AsyncMock(
        return_value={
            "asset_id": ASSET_UUID,
            "timestamp_utc": "2026-03-09T14:00:00",
            "results": {
                "soc": {"success": True, "error": None},
            },
        }
    )
    return client
