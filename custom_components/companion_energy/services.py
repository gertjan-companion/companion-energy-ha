"""HA services for Companion Energy."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

from .api_client import CompanionEnergyApiClient, CompanionEnergyApiError
from .const import (
    DATA_API_CLIENT,
    DATA_ASSET_COORDINATORS,
    DOMAIN,
    SERVICE_SUBMIT_ENERGY_INTERVALS,
    SERVICE_SUBMIT_TELEMETRY,
)

_LOGGER = logging.getLogger(__name__)

_UUID_RE = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_UUID_FIELD = vol.All(str, vol.Match(_UUID_RE))

_ENERGY_DATA_POINT_SCHEMA = vol.Schema(
    {
        vol.Required("timestamp_utc"): str,
        vol.Required("energy_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)

_SUBMIT_ENERGY_INTERVALS_SCHEMA = vol.Schema(
    {
        vol.Required("customer_id"): _UUID_FIELD,
        vol.Required("asset_id"): _UUID_FIELD,
        vol.Optional("consumption"): [_ENERGY_DATA_POINT_SCHEMA],
        vol.Optional("injection"): [_ENERGY_DATA_POINT_SCHEMA],
    }
)

_SUBMIT_TELEMETRY_SCHEMA = vol.Schema(
    {
        vol.Required("customer_id"): _UUID_FIELD,
        vol.Required("asset_id"): _UUID_FIELD,
        vol.Optional("timestamp_utc"): str,
        vol.Optional("soc"): vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
        vol.Optional("power_kw"): vol.Coerce(float),
        vol.Optional("consumption_kwh"): vol.Coerce(float),
        vol.Optional("injection_kwh"): vol.Coerce(float),
    }
)


def async_register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register integration services (idempotent — only registers once)."""
    if hass.services.has_service(DOMAIN, SERVICE_SUBMIT_TELEMETRY):
        return

    def _get_api_client(entry_id: str) -> CompanionEnergyApiClient:
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id)
        if not entry_data:
            raise HomeAssistantError("Companion Energy integration is not loaded.")
        return entry_data[DATA_API_CLIENT]

    async def handle_submit_energy_intervals(call: ServiceCall) -> None:
        customer_id: str = call.data["customer_id"]
        asset_id: str = call.data["asset_id"]
        consumption: list | None = call.data.get("consumption")
        injection: list | None = call.data.get("injection")

        if not consumption and not injection:
            raise ServiceValidationError(
                "At least one of consumption or injection must be provided."
            )

        api_client = _get_api_client(entry.entry_id)

        try:
            result = await api_client.submit_energy_intervals(
                customer_id,
                asset_id,
                consumption=consumption,
                injection=injection,
            )
        except CompanionEnergyApiError as exc:
            raise HomeAssistantError(
                f"Energy interval submission failed: {exc}"
            ) from exc

        _LOGGER.debug("Energy intervals result for %s: %s", asset_id, result)

        hass.bus.async_fire(
            f"{DOMAIN}_energy_intervals_result",
            {
                "asset_id": asset_id,
                "customer_id": customer_id,
                "consumption_points": result.get("consumption_points"),
                "injection_points": result.get("injection_points"),
            },
        )

    async def handle_submit_telemetry(call: ServiceCall) -> None:
        customer_id: str = call.data["customer_id"]
        asset_id: str = call.data["asset_id"]

        # Mutual exclusion: power_kw vs energy counters
        has_power = "power_kw" in call.data
        has_energy = "consumption_kwh" in call.data or "injection_kwh" in call.data
        if has_power and has_energy:
            raise ServiceValidationError(
                "power_kw and consumption_kwh/injection_kwh are mutually exclusive."
            )

        payload: dict[str, Any] = {
            k: v
            for k, v in call.data.items()
            if k not in ("customer_id", "asset_id") and v is not None
        }

        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        api_client = _get_api_client(entry.entry_id)

        try:
            result = await api_client.submit_telemetry(customer_id, asset_id, payload)
        except CompanionEnergyApiError as exc:
            raise HomeAssistantError(f"Telemetry submission failed: {exc}") from exc

        _LOGGER.debug("Telemetry result for %s: %s", asset_id, result)

        # Fire event so automations can react
        hass.bus.async_fire(
            f"{DOMAIN}_telemetry_result",
            {
                "asset_id": asset_id,
                "customer_id": customer_id,
                "results": result.get("results", {}),
            },
        )

        # If SOC was submitted and succeeded, update the coordinator immediately
        submitted_soc: float | None = payload.get("soc")
        if submitted_soc is not None and entry_data:
            results = result.get("results", {})
            soc_success = results.get("soc", {}).get("success", False)
            if soc_success:
                asset_coordinators = (entry_data or {}).get(DATA_ASSET_COORDINATORS, {})
                coordinator = asset_coordinators.get(customer_id)
                if coordinator and coordinator.data:
                    updated_data = dict(coordinator.data)
                    updated_data["last_soc"] = {
                        **coordinator.data.get("last_soc", {}),
                        asset_id: submitted_soc,
                    }
                    coordinator.async_set_updated_data(updated_data)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SUBMIT_ENERGY_INTERVALS,
        handle_submit_energy_intervals,
        schema=_SUBMIT_ENERGY_INTERVALS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SUBMIT_TELEMETRY,
        handle_submit_telemetry,
        schema=_SUBMIT_TELEMETRY_SCHEMA,
    )
