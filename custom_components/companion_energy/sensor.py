"""Sensor platform for Companion Energy."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import CompanionEnergyAssetCoordinator

from .const import (
    ASSET_TYPE_BATTERY,
    CONF_BASE_URL,
    DATA_ASSET_COORDINATORS,
    DOMAIN,
)
from .entity_base import CompanionEnergyEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    base_url: str = entry.data[CONF_BASE_URL]

    entities: list[SensorEntity] = []

    # Asset sensors — one coordinator per customer
    for coordinator in entry_data[DATA_ASSET_COORDINATORS].values():
        for asset in coordinator.data.get("assets", []):
            uuid = asset["uuid"]
            name = asset.get("name", uuid)
            asset_type = asset.get("asset_type", "unknown")

            entities.append(
                AssetPowerSensor(coordinator, uuid, name, asset_type, base_url)
            )
            entities.append(
                AssetSteeringStateSensor(coordinator, uuid, name, asset_type, base_url)
            )
            if asset_type == ASSET_TYPE_BATTERY:
                entities.append(
                    AssetSOCSensor(coordinator, uuid, name, asset_type, base_url)
                )

    async_add_entities(entities, update_before_add=False)


# ---------------------------------------------------------------------------
# Asset sensor classes
# ---------------------------------------------------------------------------


class AssetPowerSensor(CompanionEnergyEntity, SensorEntity):
    """Current power setpoint for an asset (kW)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"
    _attr_translation_key = "power"

    def __init__(
        self,
        coordinator: CompanionEnergyAssetCoordinator,
        asset_uuid: str,
        asset_name: str,
        asset_type: str,
        base_url: str,
    ) -> None:
        super().__init__(coordinator, asset_uuid, asset_name, asset_type, base_url)
        self._attr_unique_id = f"{DOMAIN}_{asset_uuid}_power"
        self._attr_name = "Power"

    @property
    def native_value(self) -> float | None:
        setpoint = self.coordinator.data.get("setpoints", {}).get(self._asset_uuid)
        if setpoint is None:
            return None
        return setpoint.get("power_kw")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        setpoint = self.coordinator.data.get("setpoints", {}).get(self._asset_uuid, {})
        return {"steering_state": setpoint.get("steering_state")}


class AssetSteeringStateSensor(CompanionEnergyEntity, SensorEntity):
    """Current steering state for an asset (text enum)."""

    _attr_icon = "mdi:cog-transfer"

    def __init__(
        self,
        coordinator: CompanionEnergyAssetCoordinator,
        asset_uuid: str,
        asset_name: str,
        asset_type: str,
        base_url: str,
    ) -> None:
        super().__init__(coordinator, asset_uuid, asset_name, asset_type, base_url)
        self._attr_unique_id = f"{DOMAIN}_{asset_uuid}_steering_state"
        self._attr_name = "Steering State"

    @property
    def native_value(self) -> str | None:
        setpoint = self.coordinator.data.get("setpoints", {}).get(self._asset_uuid)
        if setpoint is None:
            return None
        return setpoint.get("steering_state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Find the asset metadata
        asset = next(
            (
                a
                for a in self.coordinator.data.get("assets", [])
                if a["uuid"] == self._asset_uuid
            ),
            {},
        )
        setpoint = self.coordinator.data.get("setpoints", {}).get(self._asset_uuid, {})
        return {
            "steering_enabled": asset.get("steering_enabled"),
            "nomination_enabled": asset.get("nomination_enabled"),
            "asset_type": self._asset_type,
            "scheduled_setpoints": setpoint.get("scheduled_setpoints", []),
            "config": asset.get("config", {}),
        }


class AssetSOCSensor(CompanionEnergyEntity, SensorEntity, RestoreEntity):
    """State of Charge for battery assets (%).

    SOC is *written* to the API via telemetry, not returned by any GET endpoint.
    We persist the last submitted value across HA restarts using RestoreEntity.
    """

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:battery"

    def __init__(
        self,
        coordinator: CompanionEnergyAssetCoordinator,
        asset_uuid: str,
        asset_name: str,
        asset_type: str,
        base_url: str,
    ) -> None:
        super().__init__(coordinator, asset_uuid, asset_name, asset_type, base_url)
        self._attr_unique_id = f"{DOMAIN}_{asset_uuid}_soc"
        self._attr_name = "State of Charge"
        self._soc: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last known SOC from state on HA restart."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            with contextlib.suppress(ValueError, TypeError):
                self._soc = float(last_state.state)

    @property
    def native_value(self) -> float | None:
        # Coordinator.data["last_soc"] is updated by the telemetry service
        soc_from_coordinator = self.coordinator.data.get("last_soc", {}).get(
            self._asset_uuid
        )
        if soc_from_coordinator is not None:
            self._soc = soc_from_coordinator * 100  # API uses 0-1, HA expects %
        return self._soc
