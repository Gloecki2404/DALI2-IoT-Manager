"""Render the add-on icon.png / logo.png without third-party packages.

Run: python tools/make_icons.py
"""

import math
import pathlib
import struct
import zlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "dali2_iot_manager"


def png(path: pathlib.Path, w: int, h: int, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in pixels)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(data)


def inside_icon(x: float, y: float) -> str | None:
    """Shape test in a 48x48 design space. Returns colour key or None."""
    # rounded square background
    r = 11.0
    if not (0 <= x <= 48 and 0 <= y <= 48):
        return None
    cx = min(max(x, r), 48 - r)
    cy = min(max(y, r), 48 - r)
    if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
        return None
    # bulb glass
    if (x - 24) ** 2 + (y - 20) ** 2 <= 10.5**2 and y <= 27:
        return "white"
    if 18.5 <= x <= 29.5 and 24 <= y <= 34 and abs(x - 24) <= 5.5 + max(0.0, (29 - y)) * 0.55:
        return "white"
    # base rings
    if 19.5 <= x <= 28.5 and 35.5 <= y <= 37.5:
        return "white"
    if 21 <= x <= 27 and 39 <= y <= 41:
        return "white"
    # rays
    for ang in (-60, -30, 0, 30, 60):
        a = math.radians(ang - 90)
        for t in (14.5, 15.5, 16.5, 17.5):
            px, py = 24 + math.cos(a) * t, 20 + math.sin(a) * t
            if (x - px) ** 2 + (y - py) ** 2 <= 1.25**2:
                return "ray"
    return "bg"


def render(size: int, pad: float = 0.0) -> list[list[tuple[int, int, int, int]]]:
    ss = 4
    rows = []
    for j in range(size):
        row = []
        for i in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sj in range(ss):
                for si in range(ss):
                    x = ((i + (si + 0.5) / ss) / size) * (48 + 2 * pad) - pad
                    y = ((j + (sj + 0.5) / ss) / size) * (48 + 2 * pad) - pad
                    k = inside_icon(x, y)
                    if k is None:
                        continue
                    if k == "white":
                        c = (255, 255, 255)
                    elif k == "ray":
                        c = (225, 245, 254)
                    else:  # gradient background
                        t = (x + y) / 96
                        c = (int(41 + (2 - 41) * t), int(182 + (119 - 182) * t), int(246 + (189 - 246) * t))
                    acc[0] += c[0]
                    acc[1] += c[1]
                    acc[2] += c[2]
                    acc[3] += 255
            n = ss * ss
            a = acc[3] / n
            if a == 0:
                row.append((0, 0, 0, 0))
            else:
                cover = acc[3] / 255
                row.append((int(acc[0] / cover), int(acc[1] / cover), int(acc[2] / cover), int(a)))
        rows.append(row)
    return rows


if __name__ == "__main__":
    png(OUT / "icon.png", 128, 128, render(128))
    png(OUT / "logo.png", 250, 250, render(250, pad=2))
    print("icons written")
