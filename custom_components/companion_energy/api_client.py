"""Async HTTP client for the Companion Energy Customer API."""

from __future__ import annotations

import logging

import aiohttp

from .const import (
    API_PATH_ASSET_SETPOINT,
    API_PATH_ASSETS,
    API_PATH_CUSTOMERS,
    API_PATH_ENERGY_INTERVALS,
    API_PATH_TELEMETRY,
)

_LOGGER = logging.getLogger(__name__)


class CompanionEnergyApiError(Exception):
    """General API error."""


class CompanionEnergyAuthError(CompanionEnergyApiError):
    """Authentication / authorisation failure (HTTP 401 or 403)."""


class CompanionEnergyApiClient:
    """Thin async wrapper around aiohttp for the Companion Energy Customer API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._session = session

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_customers(self) -> list[dict]:
        """Return list of accessible customers: [{id, name}, ...]."""
        data = await self._request("GET", API_PATH_CUSTOMERS)
        return data.get("customers", [])

    async def get_assets(self, customer_id: str) -> list[dict]:
        """Return all assets for *customer_id* with full detail fields."""
        path = API_PATH_ASSETS.format(customer_id=customer_id)
        params = {
            "fields": (
                "label,location,asset_type,customer_id,customer_name,"
                "config,nomination_enabled,steering_enabled,integrations"
            )
        }
        data = await self._request("GET", path, params=params)
        return data.get("assets", [])

    async def get_asset_setpoint(self, customer_id: str, asset_id: str) -> dict | None:
        """Return the current setpoint for an asset, or None if unavailable."""
        path = API_PATH_ASSET_SETPOINT.format(
            customer_id=customer_id, asset_id=asset_id
        )
        try:
            return await self._request("GET", path)
        except CompanionEnergyApiError as exc:
            # 404 means no setpoint while steering is inactive — not an error
            if "404" in str(exc):
                return None
            raise

    async def submit_telemetry(
        self, customer_id: str, asset_id: str, payload: dict
    ) -> dict:
        """POST telemetry data and return the response body."""
        path = API_PATH_TELEMETRY.format(customer_id=customer_id, asset_id=asset_id)
        return await self._request("POST", path, json=payload)

    async def submit_energy_intervals(
        self,
        customer_id: str,
        asset_id: str,
        *,
        consumption: list[dict] | None = None,
        injection: list[dict] | None = None,
    ) -> dict:
        """POST interval energy data for an asset and return the response body.

        Each entry in *consumption* / *injection* must be a dict with keys:
          - ``timestamp_utc`` (str): ISO 8601 UTC, e.g. ``"2025-01-15T10:00:00Z"``
          - ``energy_kwh`` (float): Non-negative kWh for that interval period.
        """
        path = API_PATH_ENERGY_INTERVALS.format(
            customer_id=customer_id, asset_id=asset_id
        )
        payload: dict = {}
        if consumption is not None:
            payload["consumption"] = consumption
        if injection is not None:
            payload["injection"] = injection
        return await self._request("POST", path, json=payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = self._base_url + path
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as resp:
                if resp.status in (401, 403):
                    body = await resp.text()
                    _LOGGER.error(
                        "Auth error HTTP %s on %s %s — response: %s",
                        resp.status,
                        method,
                        url,
                        body,
                    )
                    raise CompanionEnergyAuthError(
                        f"Authentication failed: HTTP {resp.status} on {method} {url}"
                    )
                if resp.status >= 400:
                    text = await resp.text()
                    raise CompanionEnergyApiError(
                        f"HTTP {resp.status} for {method} {url}: {text}"
                    )
                return await resp.json()
        except CompanionEnergyApiError:
            raise
        except aiohttp.ClientError as exc:
            raise CompanionEnergyApiError(f"Connection error: {exc}") from exc
