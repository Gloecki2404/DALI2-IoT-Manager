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


def bank0(gtin: int, serial: int, fw: tuple[int, int] = (1, 2), units: tuple[int, int] = (1, 0)) -> dict[int, int]:
    """Memory bank 0 content (IEC 62386-102/103) for the fake bus."""
    mem = {0x09: fw[0], 0x0A: fw[1], 0x19: units[0], 0x1A: units[1]}
    mem.update({0x03 + i: b for i, b in enumerate(gtin.to_bytes(6, "big"))})
    mem.update({0x0B + i: b for i, b in enumerate(serial.to_bytes(8, "big"))})
    return mem


class FakeBus:
    """Answers raw sendDali16/24 frames like DALI gear / control devices would.

    gear[short] = {"bank0": {...}, "power_on": 254, "sysfail": 254}
    devices[short] = {"cap": 1, "app": True, "status": 0, "bank0": {...},
                      "instances": [{"type": 3, "enabled": True, "scheme": 0, "filter": 0xFF}]}
    Empty by default: nothing answers.
    """

    def __init__(self) -> None:
        self.gear: dict[int, dict[str, Any]] = {}
        self.devices: dict[int, dict[str, Any]] = {}
        self.sent16: list[dict[str, int]] = []
        self.sent24: list[dict[str, int]] = []
        self.dtr = {16: [0, 0], 24: [0, 0]}

    def _read(self, bits: int, mem: dict[int, int]) -> int | None:
        dtr = self.dtr[bits]
        value = mem.get(dtr[0]) if dtr[1] == 0 else None
        dtr[0] = (dtr[0] + 1) & 0xFF
        return value

    def frame16(self, f: dict[str, int]) -> int | None:
        self.sent16.append(f)
        a, c = f["address"], f["command"]
        if a == 0xA3:
            self.dtr[16][0] = c
            return None
        if a == 0xC3:
            self.dtr[16][1] = c
            return None
        gear = self.gear.get(a >> 1) if a <= 0x7F and a & 1 else None
        if gear is None:
            return None
        if c == 197:
            return self._read(16, gear["bank0"])
        if c == 163:
            return gear["power_on"]
        if c == 164:
            return gear["sysfail"]
        if c == 45:
            gear["power_on"] = self.dtr[16][0]
        elif c == 44:
            gear["sysfail"] = self.dtr[16][0]
        return None

    def frame24(self, f: dict[str, int]) -> int | None:
        self.sent24.append(f)
        a, i, c = f["address"], f["instance"], f["command"]
        if a == 0xC1:
            if i == 0x30:
                self.dtr[24][0] = c
            elif i == 0x31:
                self.dtr[24][1] = c
            return None
        dev = self.devices.get((a >> 1) & 0x3F) if a <= 0x7F and a & 1 else None
        if dev is None:
            return None
        if i == 0xFE:
            answers = {
                0x46: dev.get("cap", 0),
                0x30: dev.get("status", 0),
                0x3D: 0xFF if dev.get("app") else None,
                0x35: len(dev["instances"]),
            }
            if c == 0x3C:
                return self._read(24, dev.get("bank0", {}))
            return answers.get(c)
        if i >= len(dev["instances"]):
            return None
        inst = dev["instances"][i]
        return {
            0x80: inst["type"],
            0x86: 0xFF if inst.get("enabled", True) else None,
            0x8B: inst.get("scheme", 0),
            0x90: inst.get("filter", 0xFF),
        }.get(c)


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture
def gateway_api(fake_bus):
    """Patch LunatoneApi methods with fixture data; record control calls."""
    from custom_components.dali2_iot.api import LunatoneApi, LunatoneNotSupported

    calls: list[tuple[str, int | None, dict]] = []

    async def control(self, target, target_id, data):
        calls.append((target, target_id, data))

    async def not_supported(self, device_id):
        raise LunatoneNotSupported("not supported")

    async def send16(self, line, frames):
        assert len(frames) <= 16  # the gateway rejects longer requests (HTTP 422)
        return [fake_bus.frame16(f) for f in frames]

    async def send24(self, line, frames):
        assert len(frames) <= 16
        return [fake_bus.frame24(f) for f in frames]

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
        patch.object(LunatoneApi, "send_dali16", send16),
        patch.object(LunatoneApi, "send_dali24", send24),
        patch("custom_components.dali2_iot.coordinator.STARTUP_DELAY", 0),
        patch("custom_components.dali2_iot.bus.PAUSE", 0),
    ):
        yield calls
