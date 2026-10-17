"""Tests for control device discovery/settings against a simulated DALI-2 bus."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from controldevices import ControlDevices  # noqa: E402
from history import History  # noqa: E402

GTIN = 9010342012345  # Lunatone company prefix 9010342


class FakeMC:
    """A DALI-2 push button coupler with 4 instances and an application controller."""

    def __init__(self, app_enabled: bool = True) -> None:
        self.app_enabled = app_enabled
        self.instances_enabled = [False] * 4
        self.dtr0 = 0
        self.dtr1 = 0
        bank0 = [0] * 0x1B
        bank0[0] = 0x1A
        bank0[3:9] = list(GTIN.to_bytes(6, "big"))
        bank0[9:11] = [5, 2]  # firmware 5.2
        bank0[0x0B:0x13] = list((123456789).to_bytes(8, "big"))
        bank0[0x13:0x15] = [1, 0]
        bank0[0x17] = 0x08  # 103 version 2.0
        self.bank0 = bank0
        self.last_cmd: tuple | None = None

    def handle(self, instance: int, cmd: int) -> int | None:
        if instance == 0xFE:
            if cmd == 0x46:  # capabilities: app controller present + instances
                return 0b011
            if cmd == 0x30:
                return 0x08 if self.app_enabled else 0x00
            if cmd == 0x3D:
                return 0xFF if self.app_enabled else None
            if cmd == 0x35:
                return 4
            if cmd == 0x34:
                return 0x08
            if cmd in (0x3E, 0x31, 0x32):
                return 0
            if cmd == 0x3C:
                value = self.bank0[self.dtr0] if self.dtr1 == 0 and self.dtr0 < len(self.bank0) else None
                self.dtr0 += 1
                return value
            if cmd in (0x00, 0x16, 0x17, 0x01):
                # configuration commands only execute when received twice in a row
                if self.last_cmd == (instance, cmd):
                    if cmd == 0x16:
                        self.app_enabled = True
                    elif cmd == 0x17:
                        self.app_enabled = False
                    self.last_cmd = None
                else:
                    self.last_cmd = (instance, cmd)
                return None
            return None
        if instance < 4:
            if cmd == 0x80:
                return 1  # push button
            if cmd == 0x86:
                return 0xFF if self.instances_enabled[instance] else None
            if cmd == 0x8B:
                return 0
            if cmd == 0x82:
                return 0
            if cmd == 0x61:
                raise AssertionError("SET EVENT PRIORITY must never be sent by the add-on")
            if cmd in (0x62, 0x63):
                if self.last_cmd == (instance, cmd):
                    self.instances_enabled[instance] = cmd == 0x62
                    self.last_cmd = None
                else:
                    self.last_cmd = (instance, cmd)
        return None


class FakeGateway:
    def __init__(self) -> None:
        self.info = {"descriptor": {"lines": 1, "powerSupplyImplemented": False}, "lines": {}}
        self.bus = {5: FakeMC()}  # short address 5
        self.requests = 0

    async def request(self, method: str, path: str, data=None):
        assert method == "POST" and path == "/dali/sendDali24/0"
        assert len(data) <= 16
        self.requests += 1
        answers = []
        for f in data:
            a, i, c = f["address"], f["instance"], f["command"]
            if a == 0xC1:  # special command
                for dev in self.bus.values():
                    if i == 0x30:
                        dev.dtr0 = c
                    elif i == 0x31:
                        dev.dtr1 = c
                answers.append(None)
                continue
            if a == 0xFD:  # broadcast unaddressed
                answers.append(None)
                continue
            dev = self.bus.get((a >> 1) & 0x3F)
            answers.append(dev.handle(i, c) if dev else None)
        return answers


def make(tmp_path: Path) -> tuple[ControlDevices, FakeGateway]:
    gw = FakeGateway()
    return ControlDevices(gw, History(tmp_path / "db.sqlite", 30, 1000)), gw


def test_scan_finds_and_identifies_device(tmp_path: Path) -> None:
    ctrl, _ = make(tmp_path)
    result = asyncio.run(ctrl.scan())
    assert len(result["devices"]) == 1
    dev = result["devices"][0]
    assert dev["address"] == 5
    assert dev["app_controller_present"] and dev["app_controller_enabled"]
    assert dev["autark"] is True
    assert dev["manufacturer"] == "Lunatone"
    assert dev["gtin"] == str(GTIN)
    assert dev["firmware"] == "5.2"
    assert dev["serial"] == 123456789
    assert dev["version_103"] == "2.0"
    assert [i["kind"] for i in dev["instances"]] == ["push_button"] * 4
    assert dev["events_to_gateway"] is False
    assert result["unaddressed"] == {0: False}
    # cached across restarts
    ctrl2 = ControlDevices(ctrl.gateway, ctrl.history)
    assert ctrl2.cache["devices"][0]["key"] == "0_5"


def test_toggle_app_controller_and_instances(tmp_path: Path) -> None:
    ctrl, gw = make(tmp_path)
    asyncio.run(ctrl.scan())
    dev = asyncio.run(ctrl.action(0, 5, "disable_app"))
    assert gw.bus[5].app_enabled is False
    assert dev["autark"] is False
    dev = asyncio.run(ctrl.action(0, 5, "enable_instance", 2))
    assert gw.bus[5].instances_enabled == [False, False, True, False]
    assert dev["events_to_gateway"] is True
    dev = asyncio.run(ctrl.action(0, 5, "enable_app"))
    assert dev["autark"] is True
    assert ctrl.cache["devices"][0]["autark"] is True
    events = ctrl.history.events(0)
    assert any("disable_app" in e["message"] for e in events)


def test_invalid_action(tmp_path: Path) -> None:
    ctrl, _ = make(tmp_path)
    try:
        asyncio.run(ctrl.action(0, 5, "enable_instance"))
    except ValueError:
        pass
    else:
        raise AssertionError("missing instance must be rejected")


def test_direct_commands_from_other_masters(tmp_path: Path) -> None:
    ctrl, _ = make(tmp_path)
    rows = [
        (1000.0, 0, 16, "[131, 0]", 1, "command", "G1", "G1: OFF"),
        (1001.0, 0, 16, "[131, 0]", 1, "command", "G1", "G1: OFF"),
        (1002.0, 0, 16, "[7, 144]", 0, "query", "A3", "A3: QUERY STATUS"),  # gateway polling
        (1003.0, 0, 24, "[10, 4, 2]", 1, "event", "D5", "EVENT D5"),
    ]
    ctrl.history.executemany(
        "INSERT INTO monitor(ts,line,bits,data,external,kind,target,text) VALUES(?,?,?,?,?,?,?,?)", rows
    )
    import time as _t

    res = ctrl.direct_commands((_t.time() - 900) / 3600)
    assert res["commands"] == [
        {"line": 0, "target": "G1", "text": "G1: OFF", "kind": "command", "count": 2, "last": 1001.0}
    ]
    assert res["events"][0]["target"] == "D5"
