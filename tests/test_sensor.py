"""Tests for Companion Energy sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.companion_energy.sensor import (
    AssetPowerSensor,
    AssetSOCSensor,
    AssetSteeringStateSensor,
)

from .conftest import (
    ASSET_NAME,
    ASSET_UUID,
    CUSTOMER_ID,
    CUSTOMER_NAME,
    MOCK_ASSETS,
    MOCK_SETPOINT,
)


def _make_asset_coordinator(setpoint=None, last_soc=None):
    coord = MagicMock()
    coord.customer_id = CUSTOMER_ID
    coord.customer_name = CUSTOMER_NAME
    coord.data = {
        "customer_id": CUSTOMER_ID,
        "customer_name": CUSTOMER_NAME,
        "assets": MOCK_ASSETS,
        "setpoints": {ASSET_UUID: setpoint or MOCK_SETPOINT},
        "last_soc": last_soc or {},
    }
    return coord


def _make_asset_sensor(cls):
    coordinator = _make_asset_coordinator()
    sensor = cls.__new__(cls)
    sensor.coordinator = coordinator
    sensor._asset_uuid = ASSET_UUID
    sensor._asset_name = ASSET_NAME
    sensor._asset_type = "battery"
    return sensor


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------


def test_device_links_to_the_dashboard_asset_page():
    sensor = _make_asset_sensor(AssetPowerSensor)
    assert sensor.device_info["configuration_url"] == (
        f"https://my.companion.energy/app/orgs/{CUSTOMER_ID}"
        f"/control-room/assets/{ASSET_UUID}"
    )


# ---------------------------------------------------------------------------
# Power sensor
# ---------------------------------------------------------------------------


def test_power_sensor_native_value():
    sensor = _make_asset_sensor(AssetPowerSensor)
    assert sensor.native_value == -10.5


def test_power_sensor_none_when_no_setpoint():
    sensor = _make_asset_sensor(AssetPowerSensor)
    sensor.coordinator.data["setpoints"] = {}
    assert sensor.native_value is None


def test_power_sensor_attributes_contain_steering_state():
    sensor = _make_asset_sensor(AssetPowerSensor)
    attrs = sensor.extra_state_attributes
    assert attrs["steering_state"] == "discharge"


# ---------------------------------------------------------------------------
# Steering state sensor
# ---------------------------------------------------------------------------


def test_steering_state_sensor_native_value():
    sensor = _make_asset_sensor(AssetSteeringStateSensor)
    assert sensor.native_value == "discharge"


def test_steering_state_attributes():
    sensor = _make_asset_sensor(AssetSteeringStateSensor)
    attrs = sensor.extra_state_attributes
    assert attrs["steering_enabled"] is True
    assert attrs["asset_type"] == "battery"
    assert "config" in attrs


# ---------------------------------------------------------------------------
# SOC sensor
# ---------------------------------------------------------------------------


def test_soc_sensor_from_coordinator_last_soc():
    coordinator = _make_asset_coordinator(last_soc={ASSET_UUID: 0.72})
    sensor = AssetSOCSensor.__new__(AssetSOCSensor)
    sensor.coordinator = coordinator
    sensor._asset_uuid = ASSET_UUID
    sensor._asset_name = ASSET_NAME
    sensor._asset_type = "battery"
    sensor._soc = None
    assert sensor.native_value == pytest.approx(72.0)


def test_soc_sensor_falls_back_to_cached_value():
    coordinator = _make_asset_coordinator(last_soc={})
    sensor = AssetSOCSensor.__new__(AssetSOCSensor)
    sensor.coordinator = coordinator
    sensor._asset_uuid = ASSET_UUID
    sensor._asset_name = ASSET_NAME
    sensor._asset_type = "battery"
    sensor._soc = 55.0  # previously restored
    assert sensor.native_value == pytest.approx(55.0)
