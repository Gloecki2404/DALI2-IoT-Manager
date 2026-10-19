"""Raw DALI bus access through the gateway's sendDali16/24 endpoints.

Only commands defined in IEC 62386-102 (control gear) and IEC 62386-103
(control devices) are used, so this works for gear and input devices of any
manufacturer. Requests are kept short and separated by pauses so the bus load
stays well below the 75 % that Lunatone recommends as sustained maximum.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .api import LunatoneApi, LunatoneError
from .dali_decode import INSTANCE_TYPES

_LOGGER = logging.getLogger(__name__)

PAUSE = 0.3  # seconds between two gateway requests
CHUNK = 16  # the gateway accepts at most 16 frames per request

# GTIN company prefixes of known manufacturers
GTIN_PREFIXES = {"9010342": "Lunatone", "9006210": "Tridonic"}

# IEC 62386-102 (16 bit)
DTR0_16 = 0xA3
DTR1_16 = 0xC3
SET_SYSTEM_FAILURE_LEVEL = 44
SET_POWER_ON_LEVEL = 45
QUERY_POWER_ON_LEVEL = 163
QUERY_SYSTEM_FAILURE_LEVEL = 164
READ_MEMORY_LOCATION_16 = 197
MASK = 255  # "keep last level"

# IEC 62386-103 (24 bit)
DEVICE = 0xFE
SPECIAL = 0xC1
DTR0_24 = 0x30
DTR1_24 = 0x31
QUERY_DEVICE_STATUS = 0x30
QUERY_NUMBER_OF_INSTANCES = 0x35
READ_MEMORY_LOCATION_24 = 0x3C
QUERY_APPLICATION_CONTROL_ENABLED = 0x3D
QUERY_DEVICE_CAPABILITIES = 0x46
QUERY_INSTANCE_TYPE = 0x80
QUERY_INSTANCE_ENABLED = 0x86
QUERY_EVENT_SCHEME = 0x8B
QUERY_EVENT_FILTER_0_7 = 0x90

EVENT_SCHEMES = {0: "instance", 1: "device", 2: "device_instance", 3: "device_group", 4: "instance_group"}


def short_address_byte(short: int) -> int:
    """Address byte of a command to a short address (gear and devices)."""
    return ((short & 0x3F) << 1) | 1


def manufacturer_from_gtin(gtin: str | None) -> str | None:
    if not gtin:
        return None
    return next((m for p, m in GTIN_PREFIXES.items() if gtin.startswith(p)), None)


def level_to_pct(level: int | None) -> float | str | None:
    """DALI arc power level → percent; 255 (MASK) means "last level"."""
    if level is None:
        return None
    if level == MASK:
        return "last_level"
    return round(level * 100 / 254, 1)


def pct_to_level(pct: float) -> int:
    level = round(max(0.0, min(100.0, pct)) * 254 / 100)
    return 1 if pct > 0 and level == 0 else level


def _number(part: list[int | None]) -> int | None:
    if not part or any(v is None for v in part):
        return None
    return int.from_bytes(bytes(part), "big")


def parse_identity(mem: list[int | None], units: list[int | None] | None = None) -> dict[str, Any] | None:
    """Memory bank 0, offsets 0x03-0x12 (GTIN, firmware, identification number).

    ``units`` are offsets 0x19/0x1A (number of logical gear units in the bus
    unit, index of this unit) – multi-channel gear share GTIN and number.
    """
    gtin = _number(mem[0:6])
    serial = _number(mem[8:16])
    if gtin in (None, 0, 0xFFFFFFFFFFFF):
        return None
    result: dict[str, Any] = {
        "gtin": str(gtin),
        "manufacturer": manufacturer_from_gtin(str(gtin)),
        "firmware": f"{mem[6]}.{mem[7]}" if None not in mem[6:8] else None,
        "serial": serial,
        "key": None,
    }
    if serial in (None, 0, 0xFFFFFFFFFFFFFFFF):
        return result  # no usable identification number → address based identity
    key = f"g{gtin}_s{serial}"
    if units and None not in units and units[0] and units[0] > 1:
        key += f"_u{units[1]}"
        result["unit_index"] = units[1]
    result["key"] = key
    return result


async def _send16(api: LunatoneApi, line: int, frames: list[dict[str, int]]) -> list[int | None]:
    assert len(frames) <= CHUNK
    res = await api.send_dali16(line, frames)
    res = list(res) if isinstance(res, list) else []
    return res + [None] * (len(frames) - len(res))


async def _send24(api: LunatoneApi, line: int, frames: list[dict[str, int]]) -> list[int | None]:
    answers: list[int | None] = []
    for i in range(0, len(frames), CHUNK):
        if i:
            await asyncio.sleep(PAUSE)
        part = frames[i : i + CHUNK]
        res = await api.send_dali24(line, part)
        res = list(res) if isinstance(res, list) else []
        answers += res + [None] * (len(part) - len(res))
    return answers


def _f24(address: int, instance: int, command: int) -> dict[str, int]:
    return {"address": address, "instance": instance, "command": command}


# ---------------------------------------------------------------- control gear
async def read_gear(api: LunatoneApi, line: int, short: int) -> dict[str, Any]:
    """Identity (memory bank 0) and fail-safe levels of one control gear."""
    a = short_address_byte(short)
    rm = {"address": a, "command": READ_MEMORY_LOCATION_16}
    bank0 = {"address": DTR1_16, "command": 0}
    # two requests (max. 16 frames each), DTR1/DTR0 set again in each one
    first = await _send16(
        api,
        line,
        [
            {"address": a, "command": QUERY_POWER_ON_LEVEL},
            {"address": a, "command": QUERY_SYSTEM_FAILURE_LEVEL},
            bank0,
            {"address": DTR0_16, "command": 0x03},
            *[rm] * 8,  # 0x03-0x0A: GTIN + firmware, DTR0 increments after every read
        ],
    )
    if first[0] is None and first[4] is None:
        return {"power_on_level": None, "system_failure_level": None, "identity": None}
    await asyncio.sleep(PAUSE)
    second = await _send16(
        api,
        line,
        [bank0, {"address": DTR0_16, "command": 0x0B}, *[rm] * 8, {"address": DTR0_16, "command": 0x19}, rm, rm],
    )
    return {
        "power_on_level": first[0],
        "system_failure_level": first[1],
        "identity": parse_identity(first[4:12] + second[2:10], second[11:13]),
    }


async def write_gear_level(api: LunatoneApi, line: int, short: int, command: int, level: int) -> None:
    """DTR0 = level, then the configuration command twice (send-twice rule)."""
    a = short_address_byte(short)
    frames = [{"address": DTR0_16, "command": level}, {"address": a, "command": command}, {"address": a, "command": command}]
    await _send16(api, line, frames)


# ------------------------------------------------------------- control devices
async def query_instance_type(api: LunatoneApi, line: int, short: int, instance: int) -> int | None:
    res = await _send24(api, line, [_f24(short_address_byte(short), instance, QUERY_INSTANCE_TYPE)])
    return res[0]


async def read_control_device(api: LunatoneApi, line: int, short: int) -> dict[str, Any]:
    a = short_address_byte(short)
    queries = [QUERY_DEVICE_CAPABILITIES, QUERY_DEVICE_STATUS, QUERY_APPLICATION_CONTROL_ENABLED, QUERY_NUMBER_OF_INSTANCES]
    cap, status, app_enabled, n_inst = await _send24(api, line, [_f24(a, DEVICE, q) for q in queries])
    cap = cap or 0
    always_active = bool(cap & 0x04)
    app_present = bool(cap & 0x01)
    app_on = app_present and (app_enabled is not None or always_active)  # YES = 0xFF, NO = no answer
    quiescent = bool((status or 0) & 0x02)
    instances: list[dict[str, Any]] = []
    n_inst = min(n_inst or 0, 32)
    if n_inst:
        await asyncio.sleep(PAUSE)
        iq = [QUERY_INSTANCE_TYPE, QUERY_INSTANCE_ENABLED, QUERY_EVENT_SCHEME, QUERY_EVENT_FILTER_0_7]
        res = await _send24(api, line, [_f24(a, i, q) for i in range(n_inst) for q in iq])
        for i in range(n_inst):
            itype, enabled, scheme, event_filter = res[i * 4 : i * 4 + 4]
            instances.append(
                {
                    "number": i,
                    "type": itype,
                    "kind": INSTANCE_TYPES.get(itype, f"type_{itype}") if itype is not None else "unknown",
                    "enabled": enabled is not None,
                    "event_scheme": EVENT_SCHEMES.get(scheme) if scheme is not None else None,
                    "event_filter": event_filter,
                }
            )
    await asyncio.sleep(PAUSE)
    rm = _f24(a, DEVICE, READ_MEMORY_LOCATION_24)
    bank0 = _f24(SPECIAL, DTR1_24, 0)
    first = await _send24(api, line, [bank0, _f24(SPECIAL, DTR0_24, 0x03), *[rm] * 8])
    await asyncio.sleep(PAUSE)
    second = await _send24(api, line, [bank0, _f24(SPECIAL, DTR0_24, 0x0B), *[rm] * 8])
    identity = parse_identity(first[2:10] + second[2:10]) or {}
    return {
        "line": line,
        "address": short,
        "app_controller_present": app_present,
        "app_controller_enabled": app_on,
        "quiescent": quiescent,
        "instances": instances,
        # events reach the gateway only from enabled instances with a non-empty
        # event filter while the device is not in quiescent mode
        "events_to_gateway": not quiescent
        and any(i["enabled"] and i["event_filter"] != 0 for i in instances),
        "gtin": identity.get("gtin"),
        "manufacturer": identity.get("manufacturer"),
        "firmware": identity.get("firmware"),
        "serial": identity.get("serial"),
    }


async def scan_control_devices(api: LunatoneApi, lines: list[int]) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in lines:
        caps = await _send24(api, line, [_f24(short_address_byte(a), DEVICE, QUERY_DEVICE_CAPABILITIES) for a in range(64)])
        for short, cap in enumerate(caps):
            if cap is None:
                continue
            await asyncio.sleep(PAUSE)
            try:
                devices.append(await read_control_device(api, line, short))
            except LunatoneError as err:
                _LOGGER.debug("Reading control device %s/%s failed: %s", line, short, err)
    return devices


def input_keys(device: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Source keys the instances of a control device will use in their events."""
    line, short = device["line"], device["address"]
    out: list[tuple[str, dict[str, Any]]] = []
    for inst in device.get("instances", []):
        scheme, itype, num = inst.get("event_scheme"), inst.get("type"), inst["number"]
        if scheme == "instance":
            key = f"{line}_t{itype}_i{num}"
        elif scheme == "device":
            key = f"{line}_{short}_t{itype}"
        elif scheme == "device_instance":
            key = f"{line}_{short}_i{num}"
        else:
            continue  # group schemes need the group – learned from the first event
        out.append((key, inst))
    return out
