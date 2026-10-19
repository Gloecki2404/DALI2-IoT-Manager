"""Device names survive a scan that moves gear to other addresses."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import names  # noqa: E402
from history import History  # noqa: E402
from names import NameKeeper  # noqa: E402

names.PAUSE = 0
GTIN = 9010342012345


def bank0(serial: int) -> dict[int, int]:
    mem = {0x19: 1, 0x1A: 0}
    mem.update({0x03 + i: b for i, b in enumerate(GTIN.to_bytes(6, "big"))})
    mem.update({0x0B + i: b for i, b in enumerate(serial.to_bytes(8, "big"))})
    return mem


class FakeGateway:
    def __init__(self) -> None:
        self.gear = {0: bank0(100), 1: bank0(101), 2: bank0(102)}  # short address → bank 0
        self.devices = {
            1: {"id": 1, "line": 0, "address": 0, "name": "Küche"},
            2: {"id": 2, "line": 0, "address": 1, "name": "Flur"},
            3: {"id": 3, "line": 0, "address": 2, "name": "Line 0 - DALI#02"},
        }
        self.renamed: list[tuple[int, str]] = []
        self.dtr = [0, 0]

    async def snapshot(self) -> None:
        pass

    async def request(self, method: str, path: str, data=None):
        if method == "PUT":
            dev_id = int(path.rsplit("/", 1)[1])
            self.renamed.append((dev_id, data["name"]))
            return {}
        assert path == "/dali/sendDali16/0" and len(data) <= 16  # gateway limit
        out = []
        for f in data:
            a, c = f["address"], f["command"]
            if a == 0xA3:
                self.dtr[0] = c
                out.append(None)
            elif a == 0xC3:
                self.dtr[1] = c
                out.append(None)
            elif c == 197 and (a >> 1) in self.gear:
                out.append(self.gear[a >> 1].get(self.dtr[0]) if self.dtr[1] == 0 else None)
                self.dtr[0] += 1
            else:
                out.append(None)
        return out


def test_backup_and_restore_after_readdressing(tmp_path: Path) -> None:
    gw = FakeGateway()
    keeper = NameKeeper(gw, History(tmp_path / "db.sqlite", 30, 1000))
    info = asyncio.run(keeper.backup())
    assert info["count"] == 2 and info["pending"]  # default names are not backed up
    # the scan swapped the gear at A0 and A1, names stayed with the addresses
    gw.gear[0], gw.gear[1] = gw.gear[1], gw.gear[0]
    result = asyncio.run(keeper.restore())
    assert sorted(gw.renamed) == [(1, "Flur"), (2, "Küche")]
    assert result["missing"] == 0
    assert keeper.info()["pending"] is False
    # persisted across restarts
    assert NameKeeper(gw, keeper.history).info()["last_restore"]["restored"] == 2


def test_identity_key() -> None:
    mem = bank0(5)
    assert names.identity_key([mem.get(o) for o in range(3, 0x13)], [1, 0]) == f"g{GTIN}_s5"
    assert names.identity_key([mem.get(o) for o in range(3, 0x13)], [4, 3]) == f"g{GTIN}_s5_u3"
    assert names.identity_key([None] * 16, [None, None]) is None
