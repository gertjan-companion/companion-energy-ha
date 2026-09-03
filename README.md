# Companion Energy — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A [Home Assistant](https://www.home-assistant.io/) custom integration for the [Companion.energy](https://companion.energy) Customer API. Monitor your energy assets, read active steering setpoints, and push telemetry data — all from Home Assistant.

## Features

- **Asset sensors** — power (kW), steering state, and state of charge (batteries) for every configured asset
- **Telemetry service** — push power, energy counters, or SOC readings back to Companion Energy from automations
- **Steering automations** — apply CE setpoints to your hardware (see the [Huawei Solar setup guide](docs/huawei-solar-setup.md))

## Prerequisites

- Home Assistant 2024.1 or later
- [HACS](https://hacs.xyz) installed
- A Companion Energy API key (`sk-comp-...`) — generate one from the Companion Energy dashboard under **Customer → API Keys**

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/gertjan-companion/companion-energy-ha` as an **Integration**
3. Search for **Companion Energy** and install
4. Restart Home Assistant

### Manual

Copy `custom_components/companion_energy/` into your HA `config/custom_components/` directory and restart.

The Companion Energy icon and logo ship in `custom_components/companion_energy/brand/`; Home Assistant serves them from there on 2026.3 or later. Older installs fall back to a generic placeholder — the integration works either way.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Companion Energy**
3. Enter your API base URL (e.g. `https://api.companion.energy`) and API key
4. Select which customers to monitor

## Entities

### Asset sensors (one device per asset)

| Entity | Unit | Notes |
|---|---|---|
| `sensor.<asset>_power` | kW | Positive = charge/consume; negative = discharge/produce |
| `sensor.<asset>_steering_state` | — | One of: `charge`, `discharge`, `self_consumption`, `curtailment`, `max`, `off`, `consumption`, `injection`, `unsteered` |
| `sensor.<asset>_state_of_charge` | % | Batteries only; reflects the last submitted SOC |

## Services

### `companion_energy.submit_telemetry`

Submit real-time telemetry for an asset.

| Field | Type | Required | Description |
|---|---|---|---|
| `customer_id` | string | ✓ | Customer UUID |
| `asset_id` | string | ✓ | Asset UUID |
| `timestamp_utc` | string | | ISO 8601 UTC timestamp (server default: now) |
| `soc` | float (0–1) | | Battery state of charge |
| `power_kw` | float | | Instantaneous power (mutually exclusive with energy fields) |
| `consumption_kwh` | float | | Cumulative consumption counter (mutually exclusive with `power_kw`) |
| `injection_kwh` | float | | Cumulative injection counter (mutually exclusive with `power_kw`) |

Example automation:

```yaml
action:
  - service: companion_energy.submit_telemetry
    data:
      customer_id: "789e4567-e89b-12d3-a456-426614174000"
      asset_id: "456e4567-e89b-12d3-a456-426614174000"
      soc: "{{ states('sensor.my_battery_soc') | float / 100 }}"
```

## Hardware integration guides

- [Huawei Solar (EMMA + LUNA2000 + SUN2000)](docs/huawei-solar-setup.md) — telemetry push and steering automations

## Development

```bash
uv sync
uv run pre-commit install
uv run ruff check .
uv run ruff format .
uv run pytest
```

## License

MIT
