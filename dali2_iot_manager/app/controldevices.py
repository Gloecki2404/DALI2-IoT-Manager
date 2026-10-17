"""DALI-2 control devices (push buttons, sensors) – discovery and standard settings.

Only commands defined in IEC 62386-103 are used, so this works for every
manufacturer. The button → command mapping of an integrated application
controller is stored in manufacturer specific memory banks and is NOT touched.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from dali_decode import INSTANCE_TYPES

_LOGGER = logging.getLogger(__name__)

DEVICE = 0xFE  # instance byte "device"
CHUNK = 16  # frames per gateway request (gateway send buffer is 32)

# IEC 62386-103 device commands / queries (third byte)
IDENTIFY_DEVICE = 0x00
RESET_POWER_CYCLE_SEEN = 0x01
ENABLE_APPLICATION_CONTROLLER = 0x16
DISABLE_APPLICATION_CONTROLLER = 0x17
QUERY_DEVICE_STATUS = 0x30
QUERY_APPLICATION_CONTROLLER_ERROR = 0x31
QUERY_INPUT_DEVICE_ERROR = 0x32
QUERY_MISSING_SHORT_ADDRESS = 0x33
QUERY_VERSION_NUMBER = 0x34
QUERY_NUMBER_OF_INSTANCES = 0x35
READ_MEMORY_LOCATION = 0x3C
QUERY_APPLICATION_CONTROL_ENABLED = 0x3D
QUERY_OPERATING_MODE = 0x3E
QUERY_DEVICE_CAPABILITIES = 0x46
# instance commands (IEC 62386-103; 0x61 is SET EVENT PRIORITY)
ENABLE_INSTANCE = 0x62
DISABLE_INSTANCE = 0x63
QUERY_INSTANCE_TYPE = 0x80
QUERY_INSTANCE_ERROR = 0x82
QUERY_INSTANCE_ENABLED = 0x86
QUERY_EVENT_SCHEME = 0x8B
# special commands (first byte 0xC1)
SPECIAL = 0xC1
DTR0 = 0x30
DTR1 = 0x31

EVENT_SCHEMES = {0: "instance", 1: "device", 2: "device_instance", 3: "device_group", 4: "instance_group"}
MANUFACTURERS = {"9010342": "Lunatone"}  # GTIN company prefix
BANK0_LEN = 0x1B


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

    async def _send(self, line: int, frames: list[dict[str, int]]) -> list[int | None]:
        answers: list[int | None] = []
        for i in range(0, len(frames), CHUNK):
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
                    devices.append(await self.read_device(line, short, cap))
            missing = await self._send(line, [_frame(0xFD, DEVICE, QUERY_MISSING_SHORT_ADDRESS)])
            unaddressed[line] = missing[0] is not None
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
        ]
        ans = dict(zip(queries, await self._send(line, [_frame(a, DEVICE, q) for q in queries])))
        cap = ans[QUERY_DEVICE_CAPABILITIES] if ans[QUERY_DEVICE_CAPABILITIES] is not None else capabilities
        status = ans[QUERY_DEVICE_STATUS] or 0
        app_present = bool((cap or 0) & 0x01)
        always_active = bool((cap or 0) & 0x04)
        # yes/no queries: YES = 0xFF, NO = no answer
        app_enabled = ans[QUERY_APPLICATION_CONTROL_ENABLED] is not None or always_active
        n_inst = min(ans[QUERY_NUMBER_OF_INSTANCES] or 0, 32)

        instances = []
        if n_inst:
            iq = [QUERY_INSTANCE_TYPE, QUERY_INSTANCE_ENABLED, QUERY_EVENT_SCHEME, QUERY_INSTANCE_ERROR]
            frames = [_frame(a, i, q) for i in range(n_inst) for q in iq]
            res = await self._send(line, frames)
            for i in range(n_inst):
                itype, enabled, scheme, error = res[i * len(iq) : (i + 1) * len(iq)]
                instances.append(
                    {
                        "number": i,
                        "type": itype,
                        "kind": INSTANCE_TYPES.get(itype, f"type_{itype}") if itype is not None else "unknown",
                        "enabled": enabled is not None,
                        "event_scheme": EVENT_SCHEMES.get(scheme, scheme) if scheme is not None else None,
                        "error": error,
                    }
                )

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
            "instances": instances,
            "events_to_gateway": any(i["enabled"] for i in instances),
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
    async def action(self, line: int, short: int, action: str, instance: int | None = None) -> dict[str, Any]:
        a = _addr(short)
        if action == "identify":
            frames = [_frame(a, DEVICE, IDENTIFY_DEVICE)] * 2  # send twice
        elif action == "enable_app":
            frames = [_frame(a, DEVICE, ENABLE_APPLICATION_CONTROLLER)] * 2  # send twice
        elif action == "disable_app":
            frames = [_frame(a, DEVICE, DISABLE_APPLICATION_CONTROLLER)] * 2
        elif action == "reset_power_cycle":
            frames = [_frame(a, DEVICE, RESET_POWER_CYCLE_SEEN)] * 2
        elif action in ("enable_instance", "disable_instance"):
            if instance is None or not 0 <= instance <= 31:
                raise ValueError("instance number required (0-31)")
            cmd = ENABLE_INSTANCE if action == "enable_instance" else DISABLE_INSTANCE
            frames = [_frame(a, instance, cmd)] * 2
        else:
            raise ValueError(f"unknown action {action}")
        await self._send(line, frames)
        device = await self.read_device(line, short)
        devices = [d for d in self.cache.get("devices", []) if d.get("key") != device["key"]]
        self.cache["devices"] = sorted([*devices, device], key=lambda d: (d["line"], d["address"]))
        self.history.kv_set("control_devices", self.cache)
        if action != "identify":
            self.history.log_event("info", "input", f"Steuergerät L{line} D{short}: {action}", data={"instance": instance})
        return device

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
