"""Raw bus features: gear identity, fail-safe levels, control devices."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.dali2_iot import bus
from custom_components.dali2_iot.api import LunatoneApi
from custom_components.dali2_iot.const import DOMAIN

from .conftest import UID, bank0

GTIN = 9010342012345  # Lunatone prefix


def _gear(fake_bus, addresses=range(9)) -> None:
    for a in addresses:
        fake_bus.gear[a] = {"bank0": bank0(GTIN, 1000 + a), "power_on": 254, "sysfail": 254}


async def _settle(hass: HomeAssistant) -> None:
    """Let the background bus tasks and reloads run (the fake bus never blocks).
    wait_background_tasks would also wait for the endless websocket task."""
    for _ in range(100):
        await asyncio.sleep(0)
        await hass.async_block_till_done()


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await _settle(hass)


def _eid(hass: HomeAssistant, platform: str, unique_id: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)


def test_parse_identity() -> None:
    mem = bank0(GTIN, 42, fw=(3, 1))
    ident = bus.parse_identity([mem.get(o) for o in range(0x03, 0x13)], [mem[0x19], mem[0x1A]])
    assert ident == {"gtin": str(GTIN), "manufacturer": "Lunatone", "firmware": "3.1", "serial": 42, "key": f"g{GTIN}_s42"}
    # multi-channel gear: same GTIN + number, the unit index tells them apart
    mem = bank0(GTIN, 42, units=(4, 2))
    ident = bus.parse_identity([mem.get(o) for o in range(0x03, 0x13)], [mem[0x19], mem[0x1A]])
    assert ident["key"] == f"g{GTIN}_s42_u2"
    # no identification number → no identity key
    mem = bank0(GTIN, 0)
    assert bus.parse_identity([mem.get(o) for o in range(0x03, 0x13)])["key"] is None
    assert bus.parse_identity([None] * 16) is None
    assert bus.pct_to_level(100) == 254 and bus.pct_to_level(0.1) == 1 and bus.level_to_pct(255) == "last_level"


async def test_identity_migration(hass: HomeAssistant, mock_entry, gateway_api, fake_bus) -> None:
    """Address based unique IDs move to GTIN + identification number."""
    with patch("custom_components.dali2_iot.coordinator.STARTUP_DELAY", 3600):
        await _setup(hass, mock_entry)  # no bus reads yet → address based IDs
    ent_reg = er.async_get(hass)
    old = _eid(hass, "light", f"{UID}_l0_a1_light")
    assert old is not None
    device_id = ent_reg.async_get(old).device_id

    _gear(fake_bus)
    await mock_entry.runtime_data.async_read_gears(force=True)
    await _settle(hass)

    new = _eid(hass, "light", f"{UID}_g{GTIN}_s1001_light")
    assert new == old  # entity_id kept
    assert ent_reg.async_get(new).device_id == device_id  # device kept
    device = dr.async_get(hass).async_get(device_id)
    assert (DOMAIN, f"{UID}_g{GTIN}_s1001") in device.identifiers
    assert device.manufacturer == "Lunatone" and device.serial_number == "1001"
    # the unreachable DALI#04 could not be read and keeps its address based ID
    assert _eid(hass, "light", f"{UID}_l0_a4_light") is not None
    # after the reload the coordinator uses the identity directly
    assert hass.states.get(new).attributes["system_failure_level"] == 100.0


async def test_readdressing_keeps_entities(hass: HomeAssistant, mock_entry, gateway_api, fake_bus) -> None:
    """After a scan moved a gear to another address its entities follow it."""
    _gear(fake_bus)
    await _setup(hass, mock_entry)
    eid = _eid(hass, "light", f"{UID}_g{GTIN}_s1001_light")
    assert eid is not None
    coord = mock_entry.runtime_data
    # swap the gear at A0 and A1 (as a re-addressing scan may do)
    fake_bus.gear[0], fake_bus.gear[1] = fake_bus.gear[1], fake_bus.gear[0]
    await coord.async_read_gears(force=True)
    await _settle(hass)
    assert _eid(hass, "light", f"{UID}_g{GTIN}_s1001_light") == eid
    assert hass.states.get(eid).attributes["dali_address"] == 0


async def test_failsafe_levels(hass: HomeAssistant, mock_entry, gateway_api, fake_bus) -> None:
    _gear(fake_bus)
    await _setup(hass, mock_entry)
    eid = _eid(hass, "light", f"{UID}_g{GTIN}_s1001_light")
    await hass.services.async_call(
        DOMAIN,
        "set_failsafe_levels",
        {"entity_id": eid, "system_failure_level": 50, "power_on_last_level": True},
        blocking=True,
    )
    assert fake_bus.gear[1]["sysfail"] == 127
    assert fake_bus.gear[1]["power_on"] == 255
    # configuration commands are sent twice
    assert [f["command"] for f in fake_bus.sent16 if f["address"] == 3 and f["command"] in (44, 45)] == [45, 45, 44, 44]
    attrs = hass.states.get(eid).attributes
    assert attrs["system_failure_level"] == 50.0 and attrs["power_on_level"] == "last_level"


SENSOR_D0 = {
    "cap": 0x01,
    "app": True,
    "bank0": bank0(9006210737690, 77, fw=(17, 2)),
    "instances": [
        {"type": 3, "scheme": 0, "filter": 0x1F},
        {"type": 4, "scheme": 0},
        *[{"type": 1, "scheme": 0} for _ in range(13)],
    ],
}


async def test_control_device_scan(hass: HomeAssistant, mock_entry, gateway_api, fake_bus) -> None:
    sensors = [
        {"id": 0, "name": "Occupancy", "unit": "", "type": "occupancy", "value": 0, "timestamp": "",
         "addressType": "dali", "daliSensorAddress": {"line": 0, "address": 0, "instanceNumber": 0}},
    ]
    fake_bus.devices[0] = SENSOR_D0
    with patch.object(LunatoneApi, "sensors", AsyncMock(return_value=sensors)):
        await _setup(hass, mock_entry)
        coord = mock_entry.runtime_data
        found = coord.control_device(0, 0)
        assert found["app_controller_enabled"] and found["manufacturer"] == "Tridonic"
        assert found["events_to_gateway"]
        # inputs are created before the first event, with the address from the scan
        assert coord.inputs["0_t3_i0"]["short_address"] == 0
        assert coord.inputs["0_t1_i2"]["kind"] == "push_button"
        assert "0_t4_i1" not in coord.inputs  # light level reports are not learned
        failsafe = _eid(hass, "binary_sensor", f"{UID}_input_0_0_failsafe")
        assert hass.states.get(failsafe).state == STATE_ON

        occ = _eid(hass, "binary_sensor", f"{UID}_sensor0")
        assert hass.states.get(occ).state == STATE_OFF

        def frame(data):
            coord.api._test_on_message({"type": "daliMonitor", "data": {"bits": 24, "line": 0, "data": data, "externalSource": True}})

        frame([0x86, 0x80, 0x0B])  # occupied (scheme "instance", no address)
        await hass.async_block_till_done()
        assert hass.states.get(occ).state == STATE_ON  # gateway sensor follows the events
        frame([0x86, 0x80, 0x08])  # vacant
        await hass.async_block_till_done()
        assert hass.states.get(occ).state == STATE_OFF


async def test_ambiguous_inputs(hass: HomeAssistant, mock_entry, gateway_api, fake_bus) -> None:
    """Two sensors with scheme "instance" and the same instance cannot be told apart."""
    fake_bus.devices[0] = SENSOR_D0
    fake_bus.devices[3] = {**SENSOR_D0, "instances": [{"type": 3, "scheme": 0}]}
    await _setup(hass, mock_entry)
    meta = mock_entry.runtime_data.inputs["0_t3_i0"]
    assert meta["ambiguous"] is True and meta["short_address"] is None


async def test_scheme_device_instance_resolves_type(hass: HomeAssistant, mock_entry, gateway_api, fake_bus) -> None:
    """Scheme 2 events carry no instance type – it is queried once."""
    await _setup(hass, mock_entry)
    fake_bus.devices[7] = {"cap": 0, "instances": [{"type": 3}, {"type": 3}, {"type": 1, "scheme": 2}]}
    coord = mock_entry.runtime_data
    events = []
    hass.bus.async_listen("dali2_iot_input", events.append)
    value = (7 << 17) | (1 << 15) | (2 << 10) | 0b10  # D7, instance 2, short press
    for _ in range(2):
        coord.api._test_on_message(
            {"type": "daliMonitor", "data": {"bits": 24, "line": 0, "data": [value >> 16, (value >> 8) & 255, value & 255]}}
        )
        await _settle(hass)
    assert [e.data["type"] for e in events] == ["short_press", "short_press"]
    assert coord.inputs["0_7_i2"]["kind"] == "push_button"
    assert [f for f in fake_bus.sent24 if f["command"] == 0x80] == [{"address": 15, "instance": 2, "command": 0x80}]
