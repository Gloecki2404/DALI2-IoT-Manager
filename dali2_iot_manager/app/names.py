"""Back up device names before a DALI scan and restore them afterwards.

A scan – even one "without addressing" – can give gear a new short address
(the gateway's addressing macro resolves duplicates). The gateway stores names
per device/address, so names end up on the wrong gear or get lost. The backup
is keyed by the identity every gear carries in memory bank 0 (GTIN +
identification number, IEC 62386-102), which does not change with the address.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)

PAUSE = 0.3  # seconds between two gear reads
DEFAULT_NAME = re.compile(r"^Line \d+ - DALI#\d+$")  # name the gateway assigns itself

DTR0 = 0xA3
DTR1 = 0xC3
READ_MEMORY_LOCATION = 197


def _number(part: list[int | None]) -> int | None:
    if not part or any(v is None for v in part):
        return None
    return int.from_bytes(bytes(part), "big")


def identity_key(mem: list[int | None], units: list[int | None]) -> str | None:
    """GTIN + identification number (+ unit index of multi-channel gear)."""
    gtin = _number(mem[0:6])
    serial = _number(mem[8:16])
    if gtin in (None, 0, 0xFFFFFFFFFFFF) or serial in (None, 0, 0xFFFFFFFFFFFFFFFF):
        return None
    key = f"g{gtin}_s{serial}"
    if None not in units and units[0] and units[0] > 1:
        key += f"_u{units[1]}"
    return key


class NameKeeper:
    def __init__(self, gateway: Any, history: Any) -> None:
        self.gateway = gateway
        self.history = history
        self.backup_data: dict[str, Any] = history.kv_get("name_backup") or {}
        self._lock = asyncio.Lock()

    def info(self) -> dict[str, Any]:
        b = self.backup_data
        return {
            "ts": b.get("ts"),
            "count": len(b.get("entries", {})),
            "pending": bool(b.get("pending")),
            "last_restore": b.get("last_restore"),
        }

    async def _send(self, line: int, frames: list[dict[str, int]]) -> list[int | None]:
        res = await self.gateway.request("POST", f"/dali/sendDali16/{line}", frames)
        res = list(res) if isinstance(res, list) else []
        return res + [None] * (len(frames) - len(res))

    async def read_identity(self, line: int, short: int) -> str | None:
        """Memory bank 0 in two requests – the gateway accepts at most 16 frames."""
        a = ((short & 0x3F) << 1) | 1
        rm = {"address": a, "command": READ_MEMORY_LOCATION}
        bank0 = {"address": DTR1, "command": 0}
        first = await self._send(line, [bank0, {"address": DTR0, "command": 0x03}, *[rm] * 8])
        if all(v is None for v in first):
            return None
        await asyncio.sleep(PAUSE)
        second = await self._send(
            line, [bank0, {"address": DTR0, "command": 0x0B}, *[rm] * 8, {"address": DTR0, "command": 0x19}, rm, rm]
        )
        return identity_key(first[2:10] + second[2:10], second[11:13])

    async def _identities(self) -> dict[int, str]:
        """device id → identity key for all reachable gear."""
        out: dict[int, str] = {}
        for dev_id, dev in list(self.gateway.devices.items()):
            if dev.get("address") is None or not dev.get("available", True):
                continue
            try:
                key = await self.read_identity(int(dev.get("line", 0)), int(dev["address"]))
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Identity of device %s not readable: %s", dev_id, err)
                key = None
            if key:
                out[dev_id] = key
            await asyncio.sleep(PAUSE)
        return out

    async def backup(self) -> dict[str, Any]:
        async with self._lock:
            idents = await self._identities()
            entries: dict[str, dict[str, Any]] = {}
            seen: set[str] = set()
            for dev_id, key in idents.items():
                if key in seen:  # identical identity → cannot be told apart
                    entries.pop(key, None)
                    continue
                seen.add(key)
                dev = self.gateway.devices.get(dev_id) or {}
                name = dev.get("name") or ""
                if name and not DEFAULT_NAME.match(name):
                    entries[key] = {"name": name, "line": dev.get("line", 0), "address": dev.get("address")}
            self.backup_data = {
                "ts": time.time(),
                "entries": entries,
                "pending": True,
                "devices": len(self.gateway.devices),
                "unreadable": len(self.gateway.devices) - len(idents),
            }
            self.history.kv_set("name_backup", self.backup_data)
            self.history.log_event("info", "scan", f"Gerätenamen gesichert ({len(entries)} Namen)")
        return {**self.info(), "unreadable": self.backup_data["unreadable"]}

    async def restore(self) -> dict[str, Any]:
        """Give every gear its backed-up name again, wherever it is now."""
        async with self._lock:
            entries = self.backup_data.get("entries") or {}
            if not entries:
                return {"restored": [], "missing": 0}
            await self.gateway.snapshot()
            idents = await self._identities()
            restored: list[dict[str, Any]] = []
            found: set[str] = set()
            for dev_id, key in idents.items():
                entry = entries.get(key)
                if entry is None:
                    continue
                found.add(key)
                dev = self.gateway.devices.get(dev_id) or {}
                if dev.get("name") == entry["name"]:
                    continue
                try:
                    await self.gateway.request("PUT", f"/device/{dev_id}", {"name": entry["name"]})
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("Renaming device %s failed: %s", dev_id, err)
                    continue
                dev["name"] = entry["name"]
                restored.append(
                    {
                        "id": dev_id,
                        "name": entry["name"],
                        "old_address": entry.get("address"),
                        "address": dev.get("address"),
                    }
                )
            missing = len(entries) - len(found)
            self.backup_data["pending"] = False
            self.backup_data["last_restore"] = {"ts": time.time(), "restored": len(restored), "missing": missing}
            self.history.kv_set("name_backup", self.backup_data)
            moved = sum(1 for r in restored if r["old_address"] != r["address"])
            self.history.log_event(
                "warning" if moved or missing else "info",
                "scan",
                f"Gerätenamen wiederhergestellt: {len(restored)} ({moved} mit neuer Adresse), {missing} nicht gefunden",
                data={"restored": restored},
            )
        return {"restored": restored, "missing": missing}
