"""Tests for the Companion Energy config flow."""

from __future__ import annotations

import pytest

from custom_components.companion_energy.config_flow import _API_KEY_RE


@pytest.mark.parametrize(
    "api_key",
    [
        "sk-comp-legacydbkey==",  # legacy DB-backed key
        "sk_live_9YZq3TnB4xK7",  # WorkOS key — what new customer keys look like
        "sk_local_1c0e4b2a-3f5d-4a6b-8c9d-0e1f2a3b4c5d",  # fake IdP, local dev
    ],
)
def test_accepts_both_key_systems(api_key):
    assert _API_KEY_RE.match(api_key)


@pytest.mark.parametrize(
    "api_key",
    [
        "",
        "sk-comp-",
        "sk_",
        "sk_live_",
        "hunter2",
        "Bearer sk_live_abc12345",
        "sk_live abc12345",
    ],
)
def test_rejects_malformed_keys(api_key):
    assert _API_KEY_RE.match(api_key) is None
