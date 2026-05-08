"""Tests for the Companion Energy API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.companion_energy.api_client import (
    CompanionEnergyApiClient,
    CompanionEnergyApiError,
    CompanionEnergyAuthError,
)

BASE_URL = "https://api.companion.energy"
API_KEY = "sk-comp-testkey=="


def _make_response(status: int, json_data: dict | None = None, text: str = ""):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.fixture
def mock_session():
    session = MagicMock(spec=aiohttp.ClientSession)
    session.request = MagicMock()
    return session


@pytest.fixture
def client(mock_session):
    return CompanionEnergyApiClient(BASE_URL, API_KEY, mock_session)


async def test_get_customers_success(client, mock_session):
    mock_session.request.return_value = _make_response(
        200, {"customers": [{"id": "1", "name": "Acme"}]}
    )
    result = await client.get_customers()
    assert result == [{"id": "1", "name": "Acme"}]


async def test_get_customers_auth_error(client, mock_session):
    mock_session.request.return_value = _make_response(401)
    with pytest.raises(CompanionEnergyAuthError):
        await client.get_customers()


async def test_get_customers_server_error(client, mock_session):
    mock_session.request.return_value = _make_response(
        500, text="Internal Server Error"
    )
    with pytest.raises(CompanionEnergyApiError):
        await client.get_customers()


async def test_get_assets(client, mock_session):
    mock_session.request.return_value = _make_response(
        200,
        {
            "assets": [
                {
                    "uuid": "abc",
                    "name": "Battery",
                    "asset_type": "battery",
                    "config": {},
                    "steering_enabled": True,
                    "nomination_enabled": False,
                }
            ]
        },
    )
    result = await client.get_assets("cust-1")
    assert len(result) == 1
    assert result[0]["uuid"] == "abc"


async def test_get_asset_setpoint_404_returns_none(client, mock_session):
    mock_session.request.return_value = _make_response(404, text="Not Found")
    result = await client.get_asset_setpoint("cust-1", "asset-1")
    assert result is None


async def test_submit_telemetry(client, mock_session):
    mock_session.request.return_value = _make_response(
        200,
        {
            "asset_id": "asset-1",
            "timestamp_utc": "2026-03-09T14:00:00",
            "results": {"soc": {"success": True, "error": None}},
        },
    )
    result = await client.submit_telemetry("cust-1", "asset-1", {"soc": 0.8})
    assert result["results"]["soc"]["success"] is True


async def test_base_url_trailing_slash_stripped():
    session = MagicMock(spec=aiohttp.ClientSession)
    resp = _make_response(200, {"customers": []})
    session.request.return_value = resp
    client = CompanionEnergyApiClient(BASE_URL + "/", API_KEY, session)
    await client.get_customers()
    call_args = session.request.call_args
    url = call_args[0][1] if call_args[0] else call_args[1]["url"]
    assert not url.startswith(BASE_URL + "//")
