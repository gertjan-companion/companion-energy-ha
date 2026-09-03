"""Config flow for Companion Energy."""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api_client import (
    CompanionEnergyApiClient,
    CompanionEnergyApiError,
    CompanionEnergyAuthError,
)
from .const import CONF_API_KEY, CONF_BASE_URL, CONF_CUSTOMERS, DOMAIN

# Two key systems are live: the legacy DB keys (`sk-comp-...`) and the
# WorkOS-issued ones every new customer key now gets (`sk_live_...`). The API
# validates against both, so this is deliberately only a shape check — enough to
# catch a pasted password or a truncated key, without encoding either system's
# prefix. The API is the authority on whether a key is valid.
_API_KEY_RE = re.compile(r"^sk[-_][A-Za-z0-9+/=_\-]{8,}$")


def _is_local_host(host: str) -> bool:
    """Return True for hostnames safe to use over plain HTTP (loopback only)."""
    if not host:
        return False
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validate_base_url(base_url: str) -> str | None:
    """Return an error key if *base_url* is unsafe, otherwise None."""
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return "invalid_url"
    if parsed.scheme == "http" and not _is_local_host(parsed.hostname):
        return "insecure_url"
    return None


class CompanionEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI-driven setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str = ""
        self._api_key: str = ""
        self._all_customers: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Ask for base URL and API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            api_key = user_input[CONF_API_KEY].strip()

            # Prevent duplicate entries for the same API key
            self._async_abort_entries_match({CONF_API_KEY: api_key})

            url_error = _validate_base_url(base_url)
            if url_error:
                errors[CONF_BASE_URL] = url_error
            elif not _API_KEY_RE.match(api_key):
                errors[CONF_API_KEY] = "invalid_auth"
            else:
                async with aiohttp.ClientSession() as session:
                    client = CompanionEnergyApiClient(base_url, api_key, session)
                    try:
                        customers = await client.get_customers()
                    except CompanionEnergyAuthError:
                        errors[CONF_API_KEY] = "invalid_auth"
                    except CompanionEnergyApiError:
                        errors[CONF_BASE_URL] = "cannot_connect"
                    else:
                        self._base_url = base_url
                        self._api_key = api_key
                        self._all_customers = customers
                        return await self.async_step_select_customers()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL, default="https://api.companion.energy/v2"
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_customers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Let the user choose which customers to monitor.

        Auto-skipped when only one customer is available.
        """
        if not self._all_customers:
            return self.async_abort(reason="no_customers")

        # Auto-select when there is exactly one customer
        if len(self._all_customers) == 1:
            selected_ids = [self._all_customers[0]["id"]]
            return self._create_entry(selected_ids)

        errors: dict[str, str] = {}

        if user_input is not None:
            selected_ids: list[str] = user_input.get("customers", [])
            if not selected_ids:
                errors["customers"] = "no_customers_selected"
            else:
                return self._create_entry(selected_ids)

        options = [
            SelectOptionDict(value=c["id"], label=c["name"])
            for c in self._all_customers
        ]
        schema = vol.Schema(
            {
                vol.Required("customers"): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="select_customers", data_schema=schema, errors=errors
        )

    def _create_entry(self, selected_ids: list[str]) -> ConfigFlowResult:
        selected_customers = [c for c in self._all_customers if c["id"] in selected_ids]
        return self.async_create_entry(
            title="Companion Energy",
            data={
                CONF_BASE_URL: self._base_url,
                CONF_API_KEY: self._api_key,
                CONF_CUSTOMERS: selected_customers,
            },
        )
