"""DataUpdateCoordinator classes for Companion Energy."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import (
    CompanionEnergyApiClient,
    CompanionEnergyApiError,
    CompanionEnergyAuthError,
)
from .const import DOMAIN, SCAN_INTERVAL_ASSETS

_LOGGER = logging.getLogger(__name__)


class CompanionEnergyAssetCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for a single customer's assets and setpoints.

    Polls every SCAN_INTERVAL_ASSETS seconds. Data shape::

        {
            "customer_id": str,
            "customer_name": str,
            "assets": [{"uuid", "name", "asset_type", "config",
                        "steering_enabled", "nomination_enabled"}, ...],
            "setpoints": {
                "<asset_uuid>": {
                    "power_kw": float | None,
                    "steering_state": str,
                    "scheduled_setpoints": list,
                }
            },
            "last_soc": {"<asset_uuid>": float},
        }
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: CompanionEnergyApiClient,
        customer_id: str,
        customer_name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_assets_{customer_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_ASSETS),
        )
        self._api_client = api_client
        self.customer_id = customer_id
        self.customer_name = customer_name

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            assets = await self._api_client.get_assets(self.customer_id)

            # Fetch all setpoints concurrently
            setpoint_results = await asyncio.gather(
                *[
                    self._api_client.get_asset_setpoint(self.customer_id, asset["uuid"])
                    for asset in assets
                ],
                return_exceptions=True,
            )

            setpoints: dict[str, dict] = {}
            for asset, result in zip(assets, setpoint_results, strict=True):
                if isinstance(result, CompanionEnergyAuthError):
                    raise result
                if isinstance(result, Exception):
                    _LOGGER.warning(
                        "Failed to fetch setpoint for asset %s: %s",
                        asset["uuid"],
                        result,
                    )
                    setpoints[asset["uuid"]] = {
                        "power_kw": None,
                        "steering_state": "unsteered",
                        "scheduled_setpoints": [],
                    }
                elif result is None:
                    setpoints[asset["uuid"]] = {
                        "power_kw": None,
                        "steering_state": "unsteered",
                        "scheduled_setpoints": [],
                    }
                else:
                    setpoints[asset["uuid"]] = {
                        "power_kw": result.get("power_kw"),
                        "steering_state": result.get("steering_state", "unsteered"),
                        "scheduled_setpoints": result.get("scheduled_setpoints") or [],
                    }

        except CompanionEnergyAuthError as exc:
            _LOGGER.error(
                "Auth failure in asset coordinator for customer %s: %s",
                self.customer_id,
                exc,
            )
            raise ConfigEntryAuthFailed(str(exc)) from exc
        except CompanionEnergyApiError as exc:
            raise UpdateFailed(str(exc)) from exc

        # Preserve last_soc across refreshes (only telemetry writes update it)
        previous_soc: dict[str, float] = {}
        if self.data:
            previous_soc = self.data.get("last_soc", {})

        return {
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "assets": assets,
            "setpoints": setpoints,
            "last_soc": previous_soc,
        }
