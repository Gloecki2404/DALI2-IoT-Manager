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
    assert evt.attributes == {"movement": True, "occupied": True, "repeat": False, "sensor": "movement"}


def test_instance_scheme_frames_of_real_sensor():
    """Frames captured from a DALI-2 presence/light sensor (event scheme 0, no address)."""
    occ = decode_event(0, [0x86, 0x80, 0x0B])
    assert occ.scheme == "instance"
    assert (occ.instance_type, occ.instance_number, occ.short_address) == (3, 0, None)
    assert occ.event_type == "occupied"
    assert occ.attributes == {"movement": True, "occupied": True, "repeat": False, "sensor": "presence"}
    assert occ.source_key == "0_t3_i0"
    vacant_repeat = decode_event(0, [0x86, 0x80, 0x0C])
    assert vacant_repeat.event_type == "vacant" and vacant_repeat.attributes["repeat"] is True
    light = decode_event(0, [0x88, 0x85, 0xC0])
    assert (light.instance_type, light.instance_number) == (4, 1)
    assert light.kind == "light_sensor" and light.attributes == {"raw": 448}
    dec = DaliDecoder()
    assert dec.decode({"bits": 24, "data": [0x86, 0x80, 0x0B]})["target"] == "T3#0"
