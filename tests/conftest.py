"""Shared fixtures for the dali2_iot tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

FIXTURES = Path(__file__).parent / "fixtures"
HOST = "192.168.0.236"
UID = "00000000-0000-4000-8000-000000000001"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain="dali2_iot",
        title="DALI-2 IoT",
        unique_id=UID,
        data={"host": HOST},
        options={"expose_broadcast": True},
    )


@pytest.fixture
def gateway_api():
    """Patch LunatoneApi methods with fixture data; record control calls."""
    from custom_components.dali2_iot.api import LunatoneApi, LunatoneNotSupported

    calls: list[tuple[str, int | None, dict]] = []

    async def control(self, target, target_id, data):
        calls.append((target, target_id, data))

    async def not_supported(self, device_id):
        raise LunatoneNotSupported("not supported")

    async def listen(self, on_message, on_state, stop):
        self._test_on_message = on_message
        await on_state(True)
        await stop.wait()

    with (
        patch.object(LunatoneApi, "info", AsyncMock(return_value=load("info.json"))),
        patch.object(LunatoneApi, "devices", AsyncMock(return_value=load("devices.json")["devices"])),
        patch.object(LunatoneApi, "zones", AsyncMock(return_value=load("zones.json")["zones"])),
        patch.object(LunatoneApi, "sensors", AsyncMock(return_value=[])),
        patch.object(LunatoneApi, "settings", AsyncMock(return_value=load("settings.json"))),
        patch.object(LunatoneApi, "scan", AsyncMock(return_value=load("dali_scan.json"))),
        patch.object(
            LunatoneApi,
            "automations",
            AsyncMock(return_value={"sequence": [], "scheduler": [], "circadian": [], "triggerAction": []}),
        ),
        patch.object(LunatoneApi, "energy", not_supported),
        patch.object(LunatoneApi, "diagnostics", not_supported),
        patch.object(LunatoneApi, "control", control),
        patch.object(LunatoneApi, "listen", listen),
    ):
        yield calls
