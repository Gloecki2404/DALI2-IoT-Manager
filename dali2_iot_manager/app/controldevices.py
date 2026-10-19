"""DALI-2 control devices (push buttons, sensors) – discovery and standard settings.

Only commands defined in IEC 62386-103 are used, so this works for every
manufacturer. The button → command mapping of an integrated application
controller is stored in manufacturer specific memory banks and is NOT touched.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from dali_decode import INSTANCE_TYPES

_LOGGER = logging.getLogger(__name__)

DEVICE = 0xFE  # instance byte "device"
CHUNK = 16  # frames per gateway request (gateway send buffer is 32)
PAUSE = 0.3  # seconds between requests – keeps the bus load well below 75 %

# IEC 62386-103 device commands / queries (third byte)
IDENTIFY_DEVICE = 0x00
RESET_POWER_CYCLE_SEEN = 0x01
ENABLE_APPLICATION_CONTROLLER = 0x16
DISABLE_APPLICATION_CONTROLLER = 0x17
RESET = 0x10
SET_SHORT_ADDRESS = 0x14  # (DTR0) plain number 0..63 – IEC 62386-103:2020 9.14.1
ADD_TO_DEVICE_GROUPS = (0x19, 0x1A)  # groups 0-15, 16-31 (DTR2:DTR1)
REMOVE_FROM_DEVICE_GROUPS = (0x1B, 0x1C)
ENABLE_POWER_CYCLE_NOTIFICATION = 0x1F
DISABLE_POWER_CYCLE_NOTIFICATION = 0x20
SAVE_PERSISTENT_VARIABLES = 0x21
QUERY_DEVICE_STATUS = 0x30
QUERY_APPLICATION_CONTROLLER_ERROR = 0x31
QUERY_INPUT_DEVICE_ERROR = 0x32
QUERY_MISSING_SHORT_ADDRESS = 0x33
QUERY_VERSION_NUMBER = 0x34
QUERY_NUMBER_OF_INSTANCES = 0x35
READ_MEMORY_LOCATION = 0x3C
QUERY_APPLICATION_CONTROL_ENABLED = 0x3D
QUERY_OPERATING_MODE = 0x3E
QUERY_DEVICE_GROUPS = (0x41, 0x42, 0x43, 0x44)
QUERY_POWER_CYCLE_NOTIFICATION = 0x45
QUERY_DEVICE_CAPABILITIES = 0x46
# instance commands (IEC 62386-103; 0x61 is SET EVENT PRIORITY)
ENABLE_INSTANCE = 0x62
DISABLE_INSTANCE = 0x63
SET_EVENT_SCHEME = 0x67  # (DTR0)
SET_EVENT_FILTER = 0x68  # (DTR2:DTR1:DTR0)
QUERY_INSTANCE_TYPE = 0x80
QUERY_INSTANCE_ERROR = 0x82
QUERY_INSTANCE_ENABLED = 0x86
QUERY_EVENT_SCHEME = 0x8B
QUERY_EVENT_FILTER_0_7 = 0x90
QUERY_EVENT_FILTER = (0x90, 0x91, 0x92)
# special commands (first byte 0xC1)
SPECIAL = 0xC1
DTR0 = 0x30
DTR1 = 0x31
DTR2 = 0x32

# Instance settings: key → (query, set command, min, max). Values are raw DALI
# numbers – the UI converts timer steps (IEC 62386-301: 20 ms / 1 s,
# -303: 50 ms / 1 s / 10 s, -304: 50 ms / 1 s, hysteresis in %).
COMMON_SETTINGS: dict[str, tuple[int, int, int, int]] = {
    "event_priority": (0x84, 0x61, 2, 5),
    "primary_group": (0x88, 0x64, 0, 255),  # instance group 0-31, 255 = none
    "group_1": (0x89, 0x65, 0, 255),
    "group_2": (0x8A, 0x66, 0, 255),
    "event_scheme": (0x8B, 0x67, 0, 4),
}
TYPE_SETTINGS: dict[int, dict[str, tuple[int, int, int, int]]] = {
    1: {  # push button
        "short_timer": (0x0A, 0x00, 0, 255),
        "double_timer": (0x0C, 0x01, 0, 100),
        "repeat_timer": (0x0E, 0x02, 0, 255),
        "stuck_timer": (0x0F, 0x03, 0, 255),
    },
    3: {  # occupancy sensor
        "hold_timer": (0x2D, 0x21, 1, 255),
        "report_timer": (0x2E, 0x22, 0, 255),
        "deadtime_timer": (0x2C, 0x23, 0, 255),
    },
    4: {  # light sensor
        "report_timer": (0x3E, 0x30, 0, 255),
        "deadtime_timer": (0x3D, 0x32, 0, 255),
        "hysteresis": (0x3F, 0x31, 0, 25),
        "hysteresis_min": (0x3C, 0x33, 0, 255),
    },
}
TYPE_INFO: dict[int, dict[str, int]] = {
    1: {"short_timer_min": 0x0B, "double_timer_min": 0x0D},
    3: {"catching": 0x2F},
}
INSTANCE_INFO = {"resolution": 0x81, "instance_status": 0x83, "instance_error": 0x82}

EVENT_SCHEMES = {0: "instance", 1: "device", 2: "device_instance", 3: "device_group", 4: "instance_group"}
MANUFACTURERS = {"9010342": "Lunatone", "9006210": "Tridonic"}  # GTIN company prefix
SCHEME_NUMBERS = {name: num for num, name in EVENT_SCHEMES.items()}
BANK0_LEN = 0x1B


def event_key(device: dict[str, Any], inst: dict[str, Any]) -> str | None:
    """Sender key the events of an instance carry (as the integration builds it)."""
    line, short, num, itype = device["line"], device["address"], inst["number"], inst.get("type")
    return {
        "instance": f"{line}_t{itype}_i{num}",
        "device": f"{line}_{short}_t{itype}",
        "device_instance": f"{line}_{short}_i{num}",
    }.get(inst.get("event_scheme"))


def mark_ambiguous(devices: list[dict[str, Any]]) -> None:
    """Instances whose events look identical (scheme without address or number)."""
    counts: dict[str, int] = {}
    for dev in devices:
        for inst in dev.get("instances", []):
            if inst.get("enabled") and (key := event_key(dev, inst)):
                counts[key] = counts.get(key, 0) + 1
    for dev in devices:
        for inst in dev.get("instances", []):
            key = event_key(dev, inst) if inst.get("enabled") else None
            inst["ambiguous"] = bool(key and counts.get(key, 0) > 1)


def _frame(address: int, instance: int, command: int) -> dict[str, int]:
    return {"address": address, "instance": instance, "command": command}


def _addr(short: int) -> int:
    return ((short & 0x3F) << 1) | 1


def _version(v: int | None) -> str | None:
    return None if v is None else f"{v >> 2}.{v & 3}"


class ControlDevices:
    """Talks to control devices through the gateway's sendDali24 endpoint."""

    def __init__(self, gateway: Any, history: Any) -> None:
        self.gateway = gateway
        self.history = history
        self.cache: dict[str, Any] = history.kv_get("control_devices") or {"devices": [], "scanned": None}

    async def _send_groups(self, line: int, groups: list[list[dict[str, int]]]) -> None:
        """Send command groups (DTR + command twice) without splitting a group over
        two requests – the twice-sent frames must follow each other directly."""
        batch: list[dict[str, int]] = []
        for group in groups:
            assert len(group) <= CHUNK
            if len(batch) + len(group) > CHUNK:
                await self._send(line, batch)
                await asyncio.sleep(PAUSE)
                batch = []
            batch += group
        if batch:
            await self._send(line, batch)

    async def _send(self, line: int, frames: list[dict[str, int]]) -> list[int | None]:
        answers: list[int | None] = []
        for i in range(0, len(frames), CHUNK):
            if i:
                await asyncio.sleep(PAUSE)
            res = await self.gateway.request("POST", f"/dali/sendDali24/{line}", frames[i : i + CHUNK])
            chunk = res if isinstance(res, list) else []
            chunk += [None] * (len(frames[i : i + CHUNK]) - len(chunk))
            answers += chunk
        return answers

    # ------------------------------------------------------------- reading
    async def scan(self, lines: list[int] | None = None) -> dict[str, Any]:
        info = self.gateway.info or {}
        if lines is None:
            lines = list(range(int((info.get("descriptor") or {}).get("lines") or 1)))
        devices: list[dict[str, Any]] = []
        unaddressed: dict[int, bool] = {}
        for line in lines:
            caps = await self._send(line, [_frame(_addr(a), DEVICE, QUERY_DEVICE_CAPABILITIES) for a in range(64)])
            for short, cap in enumerate(caps):
                if cap is not None:
                    await asyncio.sleep(PAUSE)
                    devices.append(await self.read_device(line, short, cap))
            missing = await self._send(line, [_frame(0xFD, DEVICE, QUERY_MISSING_SHORT_ADDRESS)])
            unaddressed[line] = missing[0] is not None
        mark_ambiguous(devices)
        self.cache = {"devices": devices, "unaddressed": unaddressed, "scanned": time.time(), "lines": lines}
        self.history.kv_set("control_devices", self.cache)
        return self.cache

    async def read_device(self, line: int, short: int, capabilities: int | None = None) -> dict[str, Any]:
        a = _addr(short)
        queries = [
            QUERY_DEVICE_CAPABILITIES,
            QUERY_DEVICE_STATUS,
            QUERY_APPLICATION_CONTROL_ENABLED,
            QUERY_NUMBER_OF_INSTANCES,
            QUERY_VERSION_NUMBER,
            QUERY_OPERATING_MODE,
            QUERY_APPLICATION_CONTROLLER_ERROR,
            QUERY_INPUT_DEVICE_ERROR,
            QUERY_POWER_CYCLE_NOTIFICATION,
            *QUERY_DEVICE_GROUPS,
        ]
        ans = dict(zip(queries, await self._send(line, [_frame(a, DEVICE, q) for q in queries])))
        group_bytes = [ans[q] for q in QUERY_DEVICE_GROUPS]
        groups = (
            [g for g in range(32) if int.from_bytes(bytes(group_bytes), "little") >> g & 1]
            if None not in group_bytes
            else None
        )
        cap = ans[QUERY_DEVICE_CAPABILITIES] if ans[QUERY_DEVICE_CAPABILITIES] is not None else capabilities
        status = ans[QUERY_DEVICE_STATUS] or 0
        quiescent = bool(status & 0x02)
        app_present = bool((cap or 0) & 0x01)
        always_active = bool((cap or 0) & 0x04)
        # yes/no queries: YES = 0xFF, NO = no answer
        app_enabled = ans[QUERY_APPLICATION_CONTROL_ENABLED] is not None or always_active
        n_inst = min(ans[QUERY_NUMBER_OF_INSTANCES] or 0, 32)

        instances = []
        if n_inst:
            iq = [QUERY_INSTANCE_TYPE, QUERY_INSTANCE_ENABLED, QUERY_EVENT_SCHEME, QUERY_INSTANCE_ERROR, QUERY_EVENT_FILTER_0_7]
            frames = [_frame(a, i, q) for i in range(n_inst) for q in iq]
            await asyncio.sleep(PAUSE)
            res = await self._send(line, frames)
            for i in range(n_inst):
                itype, enabled, scheme, error, event_filter = res[i * len(iq) : (i + 1) * len(iq)]
                instances.append(
                    {
                        "number": i,
                        "type": itype,
                        "kind": INSTANCE_TYPES.get(itype, f"type_{itype}") if itype is not None else "unknown",
                        "enabled": enabled is not None,
                        "event_scheme": EVENT_SCHEMES.get(scheme, scheme) if scheme is not None else None,
                        "error": error,
                        # bit set = event is sent; no answer = instance has no filter
                        "event_filter": event_filter,
                    }
                )

        await asyncio.sleep(PAUSE)
        ident = await self._read_bank0(line, a)
        autark = app_present and app_enabled
        return {
            "line": line,
            "address": short,
            "key": f"{line}_{short}",
            "capabilities": cap,
            "app_controller_present": app_present,
            "app_controller_always_active": always_active,
            "app_controller_enabled": app_enabled,
            "app_controller_error": ans[QUERY_APPLICATION_CONTROLLER_ERROR],
            "input_device_error": ans[QUERY_INPUT_DEVICE_ERROR],
            "status": status,
            "status_flags": {
                "input_device_error": bool(status & 0x01),
                "quiescent_mode": bool(status & 0x02),
                "short_address_missing": bool(status & 0x04),
                "application_active": bool(status & 0x08),
                "application_controller_error": bool(status & 0x10),
                "power_cycle_seen": bool(status & 0x20),
                "reset_state": bool(status & 0x40),
            },
            "dali_version": _version(ans[QUERY_VERSION_NUMBER]),
            "operating_mode": ans[QUERY_OPERATING_MODE],
            "power_cycle_notification": ans[QUERY_POWER_CYCLE_NOTIFICATION] is not None,
            "device_groups": groups,
            "instances": instances,
            # events leave the device only from enabled instances with a non-empty
            # event filter, and not at all in quiescent mode
            "quiescent_mode": quiescent,
            "events_to_gateway": not quiescent and any(i["enabled"] and i["event_filter"] != 0 for i in instances),
            "autark": autark,
            **ident,
            "read_at": time.time(),
        }

    async def _read_bank0(self, line: int, a: int) -> dict[str, Any]:
        """Memory bank 0 (IEC 62386-103 identification)."""
        frames = [_frame(SPECIAL, DTR1, 0), _frame(SPECIAL, DTR0, 0)]
        frames += [_frame(a, DEVICE, READ_MEMORY_LOCATION)] * BANK0_LEN
        try:
            res = (await self._send(line, frames))[2:]
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Reading memory bank 0 failed: %s", err)
            return {}

        def num(lo: int, hi: int) -> int | None:
            part = res[lo:hi]
            if not part or any(v is None for v in part):
                return None
            return int.from_bytes(bytes(part), "big")

        gtin = num(0x03, 0x09)
        gtin_s = str(gtin) if gtin else None
        manufacturer = None
        if gtin_s:
            manufacturer = next((m for p, m in MANUFACTURERS.items() if gtin_s.startswith(p)), None)
        return {
            "gtin": gtin_s,
            "manufacturer": manufacturer,
            "firmware": f"{res[0x09]}.{res[0x0A]}" if None not in res[0x09:0x0B] else None,
            "serial": num(0x0B, 0x13),
            "hardware": f"{res[0x13]}.{res[0x14]}" if None not in res[0x13:0x15] else None,
            "version_103": _version(res[0x17]) if len(res) > 0x17 else None,
        }

    # ------------------------------------------------------------- writing
    async def action(
        self, line: int, short: int, action: str, instance: int | None = None, value: Any = None
    ) -> dict[str, Any]:
        a = _addr(short)
        if action == "identify":
            frames = [_frame(a, DEVICE, IDENTIFY_DEVICE)] * 2  # send twice
        elif action == "enable_app":
            frames = [_frame(a, DEVICE, ENABLE_APPLICATION_CONTROLLER)] * 2  # send twice
        elif action == "disable_app":
            frames = [_frame(a, DEVICE, DISABLE_APPLICATION_CONTROLLER)] * 2
        elif action == "reset_power_cycle":
            frames = [_frame(a, DEVICE, RESET_POWER_CYCLE_SEEN)] * 2
        elif action == "reset":
            # IEC 62386-103 RESET: all settings back to their reset values
            # (short address and the manufacturer specific configuration stay)
            frames = [_frame(a, DEVICE, RESET)] * 2
        elif action in ("enable_instance", "disable_instance"):
            if instance is None or not 0 <= instance <= 31:
                raise ValueError("instance number required (0-31)")
            cmd = ENABLE_INSTANCE if action == "enable_instance" else DISABLE_INSTANCE
            frames = [_frame(a, instance, cmd)] * 2
        elif action == "set_event_scheme":
            if instance is None or not 0 <= instance <= 31:
                raise ValueError("instance number required (0-31)")
            scheme = SCHEME_NUMBERS.get(value, value)
            if not isinstance(scheme, int) or not 0 <= scheme <= 4:
                raise ValueError("event scheme 0-4 required")
            # DTR0 = scheme, then SET EVENT SCHEME twice (stored non-volatile)
            frames = [_frame(SPECIAL, DTR0, scheme), _frame(a, instance, SET_EVENT_SCHEME), _frame(a, instance, SET_EVENT_SCHEME)]
        else:
            raise ValueError(f"unknown action {action}")
        if action != "identify":
            # as DALI Cockpit does: store the new settings in NVM right away
            frames += [_frame(a, DEVICE, SAVE_PERSISTENT_VARIABLES)] * 2
        await self._send(line, frames)
        if action != "identify":
            await asyncio.sleep(0.3)  # the device may not answer while writing its NVM
        device = await self.read_device(line, short)
        devices = [d for d in self.cache.get("devices", []) if d.get("key") != device["key"]]
        self.cache["devices"] = sorted([*devices, device], key=lambda d: (d["line"], d["address"]))
        mark_ambiguous(self.cache["devices"])
        self.history.kv_set("control_devices", self.cache)
        if action != "identify":
            self.history.log_event(
                "info", "input", f"Steuergerät L{line} D{short}: {action}", data={"instance": instance, "value": value}
            )
        return device

    # ------------------------------------------------------------ settings
    async def read_instance(self, line: int, short: int, number: int) -> dict[str, Any]:
        """All standard settings of one instance (IEC 62386-103 + 301/303/304)."""
        if not 0 <= number <= 31:
            raise ValueError("instance number 0-31")
        a = _addr(short)
        itype = (await self._send(line, [_frame(a, number, QUERY_INSTANCE_TYPE)]))[0]
        settings = {**COMMON_SETTINGS, **TYPE_SETTINGS.get(itype, {})}
        queries: list[tuple[str, int]] = [("enabled", QUERY_INSTANCE_ENABLED)]
        queries += [(key, spec[0]) for key, spec in settings.items()]
        queries += [(f"filter{i}", q) for i, q in enumerate(QUERY_EVENT_FILTER)]
        queries += list(TYPE_INFO.get(itype, {}).items()) + list(INSTANCE_INFO.items())
        await asyncio.sleep(PAUSE)
        res = dict(zip([k for k, _ in queries], await self._send(line, [_frame(a, number, q) for _, q in queries])))
        filters = [res[f"filter{i}"] for i in range(3)]
        return {
            "line": line,
            "address": short,
            "number": number,
            "type": itype,
            "kind": INSTANCE_TYPES.get(itype, f"type_{itype}") if itype is not None else "unknown",
            "enabled": res["enabled"] is not None,
            "settings": {key: res[key] for key in settings},
            # no answer for all three bytes: the instance has no event filter
            "event_filter": None if all(f is None for f in filters) else sum((f or 0) << (8 * i) for i, f in enumerate(filters)),
            "info": {key: res[key] for key, _ in queries if key in INSTANCE_INFO or key in TYPE_INFO.get(itype, {})},
        }

    async def configure_instance(self, line: int, short: int, number: int, changes: dict[str, Any]) -> dict[str, Any]:
        """Write the given settings (DTR0 + command twice each), then store them."""
        if not 0 <= number <= 31:
            raise ValueError("instance number 0-31")
        a = _addr(short)
        itype = (await self._send(line, [_frame(a, number, QUERY_INSTANCE_TYPE)]))[0]
        settings = {**COMMON_SETTINGS, **TYPE_SETTINGS.get(itype, {})}
        groups: list[list[dict[str, int]]] = []
        for key, value in changes.items():
            if key == "enabled":
                cmd = ENABLE_INSTANCE if value else DISABLE_INSTANCE
                groups.append([_frame(a, number, cmd)] * 2)
            elif key == "event_filter":
                value = int(value)
                if not 0 <= value <= 0xFFFFFF:
                    raise ValueError("event_filter 0-0xFFFFFF")
                groups.append(
                    [
                        _frame(SPECIAL, DTR0, value & 0xFF),
                        _frame(SPECIAL, DTR1, (value >> 8) & 0xFF),
                        _frame(SPECIAL, DTR2, (value >> 16) & 0xFF),
                        *[_frame(a, number, SET_EVENT_FILTER)] * 2,
                    ]
                )
            elif key in settings:
                _query, cmd, low, high = settings[key]
                value = SCHEME_NUMBERS.get(value, value) if key == "event_scheme" else value
                value = int(value)
                if not low <= value <= high:
                    raise ValueError(f"{key}: {low}-{high}")
                if key in ("primary_group", "group_1", "group_2") and not (value <= 31 or value == 255):
                    raise ValueError(f"{key}: group 0-31 or 255 (none)")
                groups.append([_frame(SPECIAL, DTR0, value), *[_frame(a, number, cmd)] * 2])
            else:
                raise ValueError(f"unknown setting {key} for instance type {itype}")
        if not groups:
            raise ValueError("nothing to change")
        groups.append([_frame(a, DEVICE, SAVE_PERSISTENT_VARIABLES)] * 2)
        await self._send_groups(line, groups)
        await asyncio.sleep(0.3)  # NVM write
        self.history.log_event(
            "info", "input", f"Steuergerät L{line} D{short} Eingang {number + 1}: Einstellungen geändert", data=changes
        )
        instance = await self.read_instance(line, short, number)
        await asyncio.sleep(PAUSE)
        return {"instance": instance, "device": await self._refresh(line, short)}

    async def configure_device(self, line: int, short: int, changes: dict[str, Any]) -> dict[str, Any]:
        """Device level settings: power cycle notification, device groups 0-31,
        all instances on/off and – separately verified – the short address."""
        changes = dict(changes)
        new_address = changes.pop("short_address", None)
        a = _addr(short)
        groups: list[list[dict[str, int]]] = []
        for key, value in changes.items():
            if key == "all_instances":
                count = (await self._send(line, [_frame(a, DEVICE, QUERY_NUMBER_OF_INSTANCES)]))[0] or 0
                cmd = ENABLE_INSTANCE if value else DISABLE_INSTANCE
                groups += [[_frame(a, number, cmd)] * 2 for number in range(min(count, 32))]
            elif key == "power_cycle_notification":
                cmd = ENABLE_POWER_CYCLE_NOTIFICATION if value else DISABLE_POWER_CYCLE_NOTIFICATION
                groups.append([_frame(a, DEVICE, cmd)] * 2)
            elif key == "device_groups":
                wanted = {int(g) for g in value}
                if any(not 0 <= g <= 31 for g in wanted):
                    raise ValueError("device groups 0-31")
                current_bytes = await self._send(line, [_frame(a, DEVICE, q) for q in QUERY_DEVICE_GROUPS])
                if None in current_bytes:
                    raise ValueError("device groups could not be read")
                current = int.from_bytes(bytes(current_bytes), "little")
                target = sum(1 << g for g in wanted)
                for half in (0, 1):
                    for mask, cmd in (
                        ((target & ~current) >> (16 * half) & 0xFFFF, ADD_TO_DEVICE_GROUPS[half]),
                        ((current & ~target) >> (16 * half) & 0xFFFF, REMOVE_FROM_DEVICE_GROUPS[half]),
                    ):
                        if mask:
                            groups.append(
                                [
                                    _frame(SPECIAL, DTR1, mask & 0xFF),
                                    _frame(SPECIAL, DTR2, mask >> 8),
                                    *[_frame(a, DEVICE, cmd)] * 2,
                                ]
                            )
            else:
                raise ValueError(f"unknown device setting {key}")
        if groups:
            groups.append([_frame(a, DEVICE, SAVE_PERSISTENT_VARIABLES)] * 2)
            await self._send_groups(line, groups)
            await asyncio.sleep(0.3)
            self.history.log_event("info", "input", f"Steuergerät L{line} D{short}: Geräteeinstellungen geändert", data=changes)
        if new_address is not None and int(new_address) != short:
            return await self.change_short_address(line, short, int(new_address))
        return await self._refresh(line, short)

    async def change_short_address(self, line: int, short: int, new: int) -> dict[str, Any]:
        """SET SHORT ADDRESS for this one device – checked at the new address,
        because VERIFY would also confirm a misunderstood byte (KB REV46)."""
        if not 0 <= new <= 63:
            raise ValueError("short address 0-63")
        if (await self._send(line, [_frame(_addr(new), DEVICE, QUERY_DEVICE_CAPABILITIES)]))[0] is not None:
            raise ValueError(f"Adresse D{new} ist schon von einem anderen Steuergerät belegt")
        a = _addr(short)
        await self._send(line, [_frame(SPECIAL, DTR0, new), *[_frame(a, DEVICE, SET_SHORT_ADDRESS)] * 2])
        await asyncio.sleep(0.3)
        answer_new, answer_old = await self._send(
            line, [_frame(_addr(new), DEVICE, QUERY_DEVICE_CAPABILITIES), _frame(a, DEVICE, QUERY_DEVICE_CAPABILITIES)]
        )
        if answer_new is None or answer_old is not None:
            raise ValueError(f"Adresswechsel D{short} → D{new} nicht bestätigt (neu: {answer_new}, alt: {answer_old})")
        await self._send(line, [_frame(_addr(new), DEVICE, SAVE_PERSISTENT_VARIABLES)] * 2)
        await asyncio.sleep(0.3)
        self.history.log_event("warning", "input", f"Steuergerät L{line}: Kurzadresse D{short} → D{new} geändert")
        self.cache["devices"] = [d for d in self.cache.get("devices", []) if d.get("key") != f"{line}_{short}"]
        return await self._refresh(line, new)

    async def refresh(self, line: int, short: int) -> dict[str, Any]:
        """Read one device again and update the cache."""
        return await self._refresh(line, short)

    async def _refresh(self, line: int, short: int) -> dict[str, Any]:
        device = await self.read_device(line, short)
        devices = [d for d in self.cache.get("devices", []) if d.get("key") != device["key"]]
        self.cache["devices"] = sorted([*devices, device], key=lambda d: (d["line"], d["address"]))
        mark_ambiguous(self.cache["devices"])
        self.history.kv_set("control_devices", self.cache)
        return device

    def instance_type(self, line: int, short: int, number: int) -> int | None:
        """Instance type from the last scan (events in scheme "device/instance")."""
        for dev in self.cache.get("devices", []):
            if dev.get("line") == line and dev.get("address") == short:
                for inst in dev.get("instances", []):
                    if inst.get("number") == number:
                        return inst.get("type")
        return None

    def direct_commands(self, hours: float) -> dict[str, Any]:
        """Forward frames sent by other bus masters (not the gateway)."""
        since = time.time() - hours * 3600
        commands = self.history.query(
            """SELECT line, target, text, kind, COUNT(*) AS count, MAX(ts) AS last FROM monitor
               WHERE external = 1 AND bits = 16 AND kind IN ('dapc', 'command') AND ts >= ?
               GROUP BY line, target, text ORDER BY last DESC LIMIT 200""",
            (since,),
        )
        events = self.history.query(
            """SELECT line, target, COUNT(*) AS count, MAX(ts) AS last FROM monitor
               WHERE kind = 'event' AND ts >= ? GROUP BY line, target ORDER BY last DESC LIMIT 100""",
            (since,),
        )
        return {"commands": commands, "events": events}
