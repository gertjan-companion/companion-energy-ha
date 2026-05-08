"""Companion Energy integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .api_client import CompanionEnergyApiClient
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CUSTOMERS,
    DATA_API_CLIENT,
    DATA_ASSET_COORDINATORS,
    DATA_SESSION,
    DOMAIN,
)
from .coordinator import CompanionEnergyAssetCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Companion Energy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    base_url: str = entry.data[CONF_BASE_URL]
    api_key: str = entry.data[CONF_API_KEY]
    customers: list[dict] = entry.data[CONF_CUSTOMERS]

    session = aiohttp.ClientSession()
    api_client = CompanionEnergyApiClient(base_url, api_key, session)

    # One coordinator per customer
    asset_coordinators: dict[str, CompanionEnergyAssetCoordinator] = {}
    for customer in customers:
        coordinator = CompanionEnergyAssetCoordinator(
            hass,
            api_client,
            customer_id=customer["id"],
            customer_name=customer["name"],
        )
        await coordinator.async_config_entry_first_refresh()
        asset_coordinators[customer["id"]] = coordinator

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_SESSION: session,
        DATA_API_CLIENT: api_client,
        DATA_ASSET_COORDINATORS: asset_coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services after platforms are set up
    from . import services as svc

    svc.async_register_services(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        session: aiohttp.ClientSession | None = entry_data.get(DATA_SESSION)
        if session and not session.closed:
            await session.close()

    return unload_ok
