"""Tests for control device discovery/settings against a simulated DALI-2 bus."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import controldevices  # noqa: E402
from controldevices import ControlDevices  # noqa: E402
from history import History  # noqa: E402

GTIN = 9010342012345  # Lunatone company prefix 9010342
controldevices.PAUSE = 0


class FakeMC:
    """A DALI-2 push button coupler with 4 instances and an application controller."""

    def __init__(self, app_enabled: bool = True) -> None:
        self.app_enabled = app_enabled
        self.instances_enabled = [False] * 4
        self.schemes = [0] * 4
        self.filters = [0xFF, 0xFF, 0x00, 0xFF]  # instance 2 sends no events
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
        self.saved = 0
        self.dtr2 = 0
        self.moved_to: int | None = None
        self.device_groups = 0b101  # groups 0 and 2
        self.power_cycle_notification = False
        # per instance: raw settings (opcode of the query → value)
        self.inst = [
            {0x84: 3, 0x88: 255, 0x89: 255, 0x8A: 255, 0x0A: 25, 0x0B: 25, 0x0C: 0, 0x0D: 15, 0x0E: 8, 0x0F: 20, 0x81: 1, 0x83: 2, 0x82: 0}
            for _ in range(4)
        ]

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
            if cmd == 0x14:
                if self.last_cmd == (instance, cmd):
                    self.last_cmd = None
                    self.moved_to = self.dtr0  # plain number (103:2020 9.14.1)
                else:
                    self.last_cmd = (instance, cmd)
                return None
            if 0x41 <= cmd <= 0x44:
                return (self.device_groups >> (8 * (cmd - 0x41))) & 0xFF
            if cmd == 0x45:
                return 0xFF if self.power_cycle_notification else None
            if cmd in (0x19, 0x1A, 0x1B, 0x1C, 0x1F, 0x20):
                if self.last_cmd == (instance, cmd):
                    self.last_cmd = None
                    mask = ((self.dtr2 << 8) | self.dtr1) << (16 if cmd in (0x1A, 0x1C) else 0)
                    if cmd in (0x19, 0x1A):
                        self.device_groups |= mask
                    elif cmd in (0x1B, 0x1C):
                        self.device_groups &= ~mask
                    else:
                        self.power_cycle_notification = cmd == 0x1F
                else:
                    self.last_cmd = (instance, cmd)
                return None
            if cmd == 0x21:
                if self.last_cmd == (instance, cmd):
                    self.saved += 1
                    self.last_cmd = None
                else:
                    self.last_cmd = (instance, cmd)
                return None
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
                return self.schemes[instance]
            if cmd == 0x90:
                return self.filters[instance]
            if cmd in (0x91, 0x92):
                return 0
            if cmd in self.inst[instance]:
                return self.inst[instance][cmd]
            # SET command → query opcode of the same setting
            setters = {0x61: 0x84, 0x64: 0x88, 0x65: 0x89, 0x66: 0x8A, 0x00: 0x0A, 0x01: 0x0C, 0x02: 0x0E, 0x03: 0x0F}
            if cmd in setters or cmd == 0x68:
                if self.last_cmd == (instance, cmd):
                    self.last_cmd = None
                    if cmd == 0x68:
                        self.filters[instance] = self.dtr0
                    else:
                        self.inst[instance][setters[cmd]] = self.dtr0
                else:
                    self.last_cmd = (instance, cmd)
                return None
            if cmd == 0x67:
                if self.last_cmd == (instance, cmd):
                    self.schemes[instance] = self.dtr0
                    self.last_cmd = None
                else:
                    self.last_cmd = (instance, cmd)
                return None
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
        for dev in self.bus.values():
            dev.last_cmd = None  # the gateway polls between requests → send-twice must stay in one request
        answers = []
        for f in data:
            a, i, c = f["address"], f["instance"], f["command"]
            if a == 0xC1:  # special command
                for dev in self.bus.values():
                    if i == 0x30:
                        dev.dtr0 = c
                    elif i == 0x31:
                        dev.dtr1 = c
                    elif i == 0x32:
                        dev.dtr2 = c
                answers.append(None)
                continue
            if a == 0xFD:  # broadcast unaddressed
                answers.append(None)
                continue
            dev = self.bus.get((a >> 1) & 0x3F)
            answers.append(dev.handle(i, c) if dev else None)
            for old, moving in list(self.bus.items()):
                if moving.moved_to is not None:
                    self.bus[moving.moved_to] = self.bus.pop(old)
                    moving.moved_to = None
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
    assert gw.bus[5].saved >= 1  # SAVE PERSISTENT VARIABLES after configuration
    assert ctrl.instance_type(0, 5, 2) == 1 and ctrl.instance_type(0, 5, 9) is None
    assert dev["autark"] is False
    dev = asyncio.run(ctrl.action(0, 5, "enable_instance", 2))
    assert gw.bus[5].instances_enabled == [False, False, True, False]
    # instance 2 is enabled but its event filter is empty → still nothing sent
    assert dev["events_to_gateway"] is False
    dev = asyncio.run(ctrl.action(0, 5, "enable_instance", 1))
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


def test_set_event_scheme_and_ambiguity(tmp_path: Path) -> None:
    ctrl, gw = make(tmp_path)
    gw.bus[5].instances_enabled = [True, True, False, False]
    dev = asyncio.run(ctrl.scan())["devices"][0]
    # scheme "device" (1) without instance number: both buttons look the same
    gw.bus[5].schemes = [1, 1, 1, 1]
    dev = asyncio.run(ctrl.action(0, 5, "set_event_scheme", 3, "device"))
    assert [i["ambiguous"] for i in dev["instances"]] == [True, True, False, False]
    dev = asyncio.run(ctrl.action(0, 5, "set_event_scheme", 0, "device_instance"))
    assert gw.bus[5].schemes[0] == 2
    assert dev["instances"][0]["event_scheme"] == "device_instance"
    assert [i["ambiguous"] for i in dev["instances"]] == [False, False, False, False]
    try:
        asyncio.run(ctrl.action(0, 5, "set_event_scheme", 0, 9))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid scheme must be rejected")


def test_instance_settings_read_and_write(tmp_path: Path) -> None:
    ctrl, gw = make(tmp_path)
    asyncio.run(ctrl.scan())
    inst = asyncio.run(ctrl.read_instance(0, 5, 1))
    assert inst["kind"] == "push_button"
    assert inst["settings"]["short_timer"] == 25 and inst["settings"]["event_priority"] == 3
    assert inst["info"]["short_timer_min"] == 25 and inst["event_filter"] == 0xFF
    changes = {"short_timer": 30, "double_timer": 15, "repeat_timer": 10, "stuck_timer": 40,
               "event_priority": 4, "primary_group": 7, "group_1": 255, "event_filter": 0xF4, "enabled": True}
    res = asyncio.run(ctrl.configure_instance(0, 5, 1, changes))
    s = res["instance"]["settings"]
    assert (s["short_timer"], s["double_timer"], s["repeat_timer"], s["stuck_timer"]) == (30, 15, 10, 40)
    assert s["event_priority"] == 4 and s["primary_group"] == 7
    assert res["instance"]["event_filter"] == 0xF4 and res["instance"]["enabled"] is True
    assert gw.bus[5].saved >= 1
    for bad in ({"event_priority": 9}, {"primary_group": 40}, {"hold_timer": 5}, {}):
        try:
            asyncio.run(ctrl.configure_instance(0, 5, 1, bad))
        except ValueError:
            continue
        raise AssertionError(f"{bad} must be rejected")


def test_device_settings(tmp_path: Path) -> None:
    ctrl, gw = make(tmp_path)
    dev = asyncio.run(ctrl.scan())["devices"][0]
    assert dev["device_groups"] == [0, 2] and dev["power_cycle_notification"] is False
    dev = asyncio.run(ctrl.configure_device(0, 5, {"device_groups": [2, 5, 17], "power_cycle_notification": True}))
    assert dev["device_groups"] == [2, 5, 17]
    assert dev["power_cycle_notification"] is True
    assert gw.bus[5].device_groups == (1 << 2) | (1 << 5) | (1 << 17)


def test_change_short_address(tmp_path: Path) -> None:
    ctrl, gw = make(tmp_path)
    asyncio.run(ctrl.scan())
    gw.bus[9] = FakeMC()  # D9 is taken
    try:
        asyncio.run(ctrl.configure_device(0, 5, {"short_address": 9}))
    except ValueError as err:
        assert "belegt" in str(err)
    else:
        raise AssertionError("taken address must be rejected")
    dev = asyncio.run(ctrl.configure_device(0, 5, {"short_address": 12}))
    assert dev["address"] == 12 and 12 in gw.bus and 5 not in gw.bus
    assert [d["key"] for d in ctrl.cache["devices"]] == ["0_12"]


def test_all_instances_switch(tmp_path: Path) -> None:
    ctrl, gw = make(tmp_path)
    asyncio.run(ctrl.scan())
    asyncio.run(ctrl.configure_device(0, 5, {"all_instances": True}))
    assert gw.bus[5].instances_enabled == [True] * 4
    asyncio.run(ctrl.configure_device(0, 5, {"all_instances": False}))
    assert gw.bus[5].instances_enabled == [False] * 4
