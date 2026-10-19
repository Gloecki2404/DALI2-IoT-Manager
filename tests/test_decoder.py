"""Tests for the DALI frame decoder (shared by add-on and integration)."""

from custom_components.dali2_iot.dali_decode import DaliDecoder, decode_event

from .conftest import load


def frame24(value: int) -> list[int]:
    return [(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF]


def test_decode_real_monitor_frames():
    dec = DaliDecoder()
    texts = [dec.decode(m["data"])["text"] for m in load("ws_messages.json")["monitor"][:4]]
    assert texts[0] == "A3: QUERY STATUS"
    assert texts[1].startswith("Answer 0") and "QUERY STATUS" in texts[1]
    assert texts[2] == "A3: QUERY ACTUAL LEVEL"


def test_decode_commands():
    dec = DaliDecoder()
    assert dec.decode({"bits": 16, "data": [0x02, 0x98]})["text"] == "A1: DAPC 152 (59.8 %)"
    assert dec.decode({"bits": 16, "data": [0xA3, 0xC8]})["text"] == "DTR0 = 200"
    assert dec.decode({"bits": 16, "data": [0xC1, 0x08]})["text"] == "ENABLE DEVICE TYPE 8"
    # extended command is resolved against the enabled device type
    assert "SET TEMPORARY COLOUR TEMPERATURE" in dec.decode({"bits": 16, "data": [0x03, 0xE7]})["text"]
    assert dec.decode({"bits": 16, "data": [0x86, 0x7F]})["text"] == "G3: DAPC 127 (50.0 %)"
    assert dec.decode({"bits": 16, "data": [0x87, 0x00]})["text"] == "G3: OFF"
    assert dec.decode({"bits": 16, "data": [0xFF, 0x00]})["text"] == "BC: OFF"
    assert dec.decode({"bits": 16, "data": [0x03, 0x25]})["text"] == "A1: IDENTIFY DEVICE"
    q = dec.decode({"bits": 24, "data": [0x0B, 0xFE, 0x30]})
    assert q["kind"] == "query" and "QUERY DEVICE STATUS" in q["text"]


def test_push_button_event():
    # instance scheme: short address 5, instance type 1 (push button), short press
    evt = decode_event(0, frame24((5 << 17) | (1 << 10) | 0b10))
    assert evt is not None
    assert evt.scheme == "device"
    assert evt.short_address == 5
    assert evt.kind == "push_button"
    assert evt.event_type == "short_press"
    assert evt.source_key == "0_5_t1"


def test_device_scheme_event_and_command_frames():
    evt = decode_event(1, frame24((12 << 17) | (1 << 15) | (3 << 10) | 0b1001))
    assert evt.scheme == "device_instance"
    assert evt.instance_number == 3
    assert evt.source_key == "1_12_i3"
    # bit 16 set → command, not an event
    assert decode_event(0, [0x0B, 0xFE, 0x30]) is None


def test_occupancy_event():
    evt = decode_event(0, frame24((7 << 17) | (3 << 10) | 0b11))
    assert evt.kind == "occupancy_sensor"
    assert evt.event_type == "occupied"
    assert evt.attributes == {"raw": 3, "movement": True, "occupied": True, "repeat": False, "sensor": "movement"}


def test_instance_scheme_frames_of_real_sensor():
    """Frames captured from a DALI-2 presence/light sensor (event scheme 0, no address)."""
    occ = decode_event(0, [0x86, 0x80, 0x0B])
    assert occ.scheme == "instance"
    assert (occ.instance_type, occ.instance_number, occ.short_address) == (3, 0, None)
    assert occ.event_type == "occupied"
    assert occ.attributes == {"raw": 11, "movement": True, "occupied": True, "repeat": False, "sensor": "presence"}
    assert occ.source_key == "0_t3_i0"
    vacant_repeat = decode_event(0, [0x86, 0x80, 0x0C])
    assert vacant_repeat.event_type == "vacant" and vacant_repeat.attributes["repeat"] is True
    light = decode_event(0, [0x88, 0x85, 0xC0])
    assert (light.instance_type, light.instance_number) == (4, 1)
    assert light.kind == "light_sensor" and light.attributes == {"raw": 448}
    dec = DaliDecoder()
    assert dec.decode({"bits": 24, "data": [0x86, 0x80, 0x0B]})["target"] == "T3#0"


def test_movement_counts_as_occupied():
    # DiiA example: event information 0x009 = movement detected (presence sensor)
    evt = decode_event(0, frame24((1 << 23) | (3 << 17) | (1 << 15) | 0x009))
    assert evt.event_type == "occupied"
    assert evt.attributes["movement"] is True and evt.attributes["raw"] == 9


def test_power_cycle_notification_mask():
    pc = decode_event(0, [0xFE, 0xE0, 0x45])  # address valid, short address 5
    assert pc.scheme == "power_cycle" and pc.attributes["short_address"] == 5
    assert "device_group" not in pc.attributes
    pc = decode_event(0, [0xFE, 0xF1, 0x80])  # group valid, group 3
    assert pc.attributes["device_group"] == 3
    # 0xFE in byte 0 alone is not a power cycle: here instance group 31, type 1
    ig = decode_event(0, [0xFE, 0x04, 0x02])
    assert ig.scheme == "instance_group" and ig.instance_group == 31 and ig.instance_type == 1
    assert ig.source_key == "0_ig31_t1"


def test_group_scheme_keys():
    dg = decode_event(2, frame24((1 << 23) | (4 << 17) | (1 << 10) | 0b10))
    assert dg.scheme == "device_group" and dg.source_key == "2_dg4_t1"


def test_instance_commands_use_instance_table():
    dec = DaliDecoder()
    r = dec.decode({"bits": 24, "data": [0x0B, 0x02, 0x00]})
    assert r["text"] == "D5 [instance 2]: SET SHORT TIMER (DTR0) [301]"
    assert dec.decode({"bits": 24, "data": [0x0B, 0xFE, 0x00]})["text"] == "D5 [device]: IDENTIFY DEVICE"
    r = dec.decode({"bits": 24, "data": [0x0B, 0x01, 0x8C]})
    assert r["kind"] == "query" and "QUERY INPUT VALUE" in r["text"]
    assert "instance group 3" in dec.decode({"bits": 24, "data": [0x0B, 0x83, 0x62]})["text"]
    assert "instance type 1" in dec.decode({"bits": 24, "data": [0x0B, 0xC1, 0x62]})["text"]
    assert "MANUFACTURER SPECIFIC" in dec.decode({"bits": 24, "data": [0x0B, 0x00, 0x41]})["text"]


def test_addressing_warning_and_specials():
    dec = DaliDecoder()
    # INITIALISE alone is harmless (DALI Cockpit sends it before every read-out)
    r = dec.decode({"bits": 16, "data": [0xA5, 0x00]})
    assert "warning" not in r and "ALL control gear" in r["text"]
    assert "without short address" in dec.decode({"bits": 16, "data": [0xA5, 0xFF]})["text"]
    assert "ALL control devices" in dec.decode({"bits": 24, "data": [0xC1, 0x01, 0xFF]})["text"]
    assert "without short address" in dec.decode({"bits": 24, "data": [0xC1, 0x01, 0x7F]})["text"]
    # RANDOMISE / PROGRAM SHORT ADDRESS really (re)assign addresses
    assert dec.decode({"bits": 16, "data": [0xA7, 0x00]})["warning"] == "addressing"
    r = dec.decode({"bits": 16, "data": [0xB7, 0x0B]})
    assert r["warning"] == "addressing" and r["text"] == "PROGRAM SHORT ADDRESS A5"
    r = dec.decode({"bits": 24, "data": [0xC1, 0x08, 0xFF]})
    assert r["warning"] == "addressing" and "delete" in r["text"]
    # control devices use the plain number (103:2020 9.14.1), gear 0AAAAAA1
    assert dec.decode({"bits": 24, "data": [0xC1, 0x08, 0x01]})["text"] == "PROGRAM SHORT ADDRESS D1"
    assert dec.decode({"bits": 24, "data": [0xC1, 0x02, 0x00]})["warning"] == "addressing"
    assert dec.decode({"bits": 24, "data": [0xC7, 0x01, 0x02]})["text"] == "DTR1:DTR0 = 1:2"
    assert dec.decode({"bits": 24, "data": [0xC5, 0x10, 0x20]})["text"] == "DIRECT WRITE MEMORY offset 16 = 32"
    assert dec.decode({"bits": 25, "data": [1, 2, 3, 4]})["kind"] == "edali"


def test_read_memory_answer_is_paired():
    dec = DaliDecoder()
    assert dec.decode({"bits": 16, "data": [0x03, 197]})["kind"] == "query"
    assert "READ MEMORY LOCATION" in dec.decode({"bits": 8, "data": [0x12]})["text"]
    assert dec.decode({"bits": 24, "data": [0x01, 0xFE, 0x3C]})["kind"] == "query"


def test_decoder_copies_identical():
    from pathlib import Path

    root = Path(__file__).parent.parent
    a = (root / "custom_components/dali2_iot/dali_decode.py").read_text(encoding="utf-8")
    b = (root / "dali2_iot_manager/app/dali_decode.py").read_text(encoding="utf-8")
    assert a.splitlines() == b.splitlines()


def test_device_instance_event_type_from_lookup():
    """Real capture after switching the sensor to scheme "device/instance"."""
    plain = DaliDecoder().decode({"bits": 24, "data": [0x00, 0x80, 0x0C]})
    assert plain["event"]["kind"] == "unknown"
    dec = DaliDecoder(instance_type=lambda line, short, num: 3 if (line, short, num) == (0, 0, 0) else None)
    r = dec.decode({"bits": 24, "line": 0, "data": [0x00, 0x80, 0x0C]})
    assert r["event"]["kind"] == "occupancy_sensor" and r["event"]["event_type"] == "vacant"
    assert "occupancy_sensor: vacant" in r["text"]
