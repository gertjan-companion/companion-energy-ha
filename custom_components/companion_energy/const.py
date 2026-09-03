"""Constants for the Companion Energy integration."""

DOMAIN = "companion_energy"

# Config entry keys
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_CUSTOMERS = "customers"

# Update intervals (seconds)
SCAN_INTERVAL_ASSETS = 30

# How many scheduled future setpoints to ask for (API accepts 1-100). 24 covers
# a day of hourly steps; automations reading the schedule can also fall back to
# it if HA loses connectivity.
SETPOINT_SCHEDULE_LIMIT = 24

# API path templates
API_PATH_CUSTOMERS = "/customers"
API_PATH_ASSETS = "/customer/{customer_id}/assets"
API_PATH_ASSET_SETPOINT = "/customer/{customer_id}/assets/{asset_id}/setpoint"
API_PATH_ENERGY_INTERVALS = "/customer/{customer_id}/assets/{asset_id}/energy-intervals"
API_PATH_TELEMETRY = "/customer/{customer_id}/assets/{asset_id}/telemetry"

# "Visit device" link — the asset's page in the Companion Energy dashboard, not
# the API. `customer_id` is the same id the API returns from /customers, and
# `asset_id` the same asset uuid, so both come straight from the coordinator.
# ponytail: production host hardcoded. Internal dev/tst dashboards live at
# my.dev/my.tst.companion.energy — make this an option if anyone actually runs
# Home Assistant against one.
DASHBOARD_ASSET_URL = (
    "https://my.companion.energy/app/orgs/{customer_id}/control-room/assets/{asset_id}"
)

# Asset types (values match the API's AssetType enum)
ASSET_TYPE_BATTERY = "battery"
ASSET_TYPE_SOLAR_PANELS = "solar panels"
ASSET_TYPE_GRID_CONNECTION = "grid connection"
ASSET_TYPE_EV_CHARGER = "ev charger"
ASSET_TYPE_ENERGY_METER = "energy meter"
ASSET_TYPE_FLEXIBLE_LOAD = "flexible load"
ASSET_TYPE_EBOILER = "e-boiler"
ASSET_TYPE_THERMAL_STORAGE = "thermal storage"

# Steering states (values match the API's SetpointSteeringState enum)
STEERING_STATES = [
    "charge",
    "discharge",
    "self consumption",
    "curtailment",
    "max",
    "off",
    "consumption",
    "injection",
    "unsteered",
]

# HA service names
SERVICE_SUBMIT_TELEMETRY = "submit_telemetry"
SERVICE_SUBMIT_ENERGY_INTERVALS = "submit_energy_intervals"

# hass.data keys
DATA_API_CLIENT = "api_client"
DATA_ASSET_COORDINATORS = "asset_coordinators"
