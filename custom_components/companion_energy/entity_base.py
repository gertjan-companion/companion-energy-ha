"""Base entity class for Companion Energy."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CompanionEnergyAssetCoordinator


class CompanionEnergyEntity(CoordinatorEntity[CompanionEnergyAssetCoordinator]):
    """Base class for all Companion Energy asset entities.

    Groups sensors per asset under a single HA device.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CompanionEnergyAssetCoordinator,
        asset_uuid: str,
        asset_name: str,
        asset_type: str,
        base_url: str,
    ) -> None:
        super().__init__(coordinator)
        self._asset_uuid = asset_uuid
        self._asset_name = asset_name
        self._asset_type = asset_type
        self._base_url = base_url

    @property
    def device_info(self) -> DeviceInfo:
        customer_id = self.coordinator.customer_id
        return DeviceInfo(
            identifiers={(DOMAIN, self._asset_uuid)},
            name=self._asset_name,
            manufacturer="Companion Energy",
            model=self._asset_type.title(),
            configuration_url=(
                f"{self._base_url}/customer/{customer_id}/assets/{self._asset_uuid}"
            ),
        )
