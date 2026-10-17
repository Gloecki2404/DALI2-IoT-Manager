"""Setup, entities, light commands and websocket handling."""

from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ATTR_TRANSITION
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.lunatone_dali.const import DOMAIN

from .conftest import UID


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _eid(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)


async def test_setup_creates_entities(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    await _setup(hass, mock_entry)
    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_entry.entry_id)
    lights = [e for e in entities if e.domain == "light"]
    # 9 DALI gear + broadcast zone + group 1 zone (groups 0/2 have no members)
    assert len(lights) == 11

    tw = hass.states.get(_eid(hass, "light", f"{UID}_l0_a1_light"))
    assert tw.state == STATE_OFF
    assert "color_temp" in tw.attributes["supported_color_modes"]
    assert tw.attributes["dali_address"] == 1

    # DALI#04 is reported unavailable by the gateway
    assert hass.states.get(_eid(hass, "light", f"{UID}_l0_a4_light")).state == STATE_UNAVAILABLE
    reach = hass.states.get(_eid(hass, "binary_sensor", f"{UID}_l0_a4_reachable"))
    assert reach.state == STATE_OFF

    total = hass.states.get(_eid(hass, "sensor", f"{UID}_devices_total"))
    assert total.state == "9"
    assert hass.states.get(_eid(hass, "binary_sensor", f"{UID}_websocket")).state == STATE_ON


async def test_light_commands(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    await _setup(hass, mock_entry)
    tw = _eid(hass, "light", f"{UID}_l0_a1_light")
    plain = _eid(hass, "light", f"{UID}_l0_a0_light")

    await hass.services.async_call("light", "turn_on", {"entity_id": plain}, blocking=True)
    assert gateway_api[-1] == ("device", 2, {"gotoLastActive": True})

    await hass.services.async_call(
        "light", "turn_on", {"entity_id": plain, ATTR_BRIGHTNESS: 128, ATTR_TRANSITION: 2}, blocking=True
    )
    assert gateway_api[-2] == ("device", 2, {"dimmableWithFade": {"dimValue": 50.2, "fadeTime": 2.0}})
    # the configured fade time of the gear (0.7 s) is restored afterwards
    assert gateway_api[-1] == ("device", 2, {"fadeTime": 0.7})

    await hass.services.async_call(
        "light", "turn_on", {"entity_id": tw, ATTR_BRIGHTNESS: 255, ATTR_COLOR_TEMP_KELVIN: 5000}, blocking=True
    )
    assert gateway_api[-1] == ("device", 1, {"dimmableKelvin": {"dimmable": 100.0, "kelvin": 5000}})
    # the real gateway switches the light on but keeps reporting the old kelvin value
    mock_entry.runtime_data.api._test_on_message(
        {
            "type": "devices",
            "data": {"devices": [{"id": 1, "features": {"switchable": {"status": True}, "dimmable": {"status": 100.0}}}]},
            "timeSignature": {"timestamp": 2.0, "counter": 7},
        }
    )
    await hass.async_block_till_done()
    # → the commanded (optimistic) value is shown
    assert hass.states.get(tw).attributes["color_temp_kelvin"] == 5000

    await hass.services.async_call("light", "turn_off", {"entity_id": plain}, blocking=True)
    assert gateway_api[-1] == ("device", 2, {"switchable": False})

    await hass.services.async_call(
        DOMAIN, "recall_scene", {"entity_id": plain, "scene": 3}, blocking=True
    )
    assert gateway_api[-1] == ("device", 2, {"scene": 3})


async def test_websocket_delta_updates(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    await _setup(hass, mock_entry)
    coord = mock_entry.runtime_data
    plain = _eid(hass, "light", f"{UID}_l0_a0_light")
    # partial update exactly as sent by the real gateway
    coord.api._test_on_message(
        {
            "type": "devices",
            "data": {
                "devices": [
                    {
                        "id": 2,
                        "status": {"raw": 12, "lampOn": True, "limitError": True, "shortAddress": False},
                        "features": {"switchable": {"status": True}, "dimmable": {"status": 39.37}},
                    }
                ]
            },
            "timeSignature": {"timestamp": 1.0, "counter": 99},
        }
    )
    await hass.async_block_till_done()
    state = hass.states.get(plain)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_BRIGHTNESS] == 100
    # features not contained in the delta are preserved
    assert "fade_time" in state.attributes and state.attributes["fade_time"] == 0.7
    assert coord.data.devices[2]["status"]["isUnaddressed"] is False


async def test_unavailable_grace_period(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    from unittest.mock import patch as _patch

    await _setup(hass, mock_entry)
    coord = mock_entry.runtime_data
    plain = _eid(hass, "light", f"{UID}_l0_a0_light")
    reach = _eid(hass, "binary_sensor", f"{UID}_l0_a0_reachable")
    coord.api._test_on_message(
        {"type": "devices", "data": {"devices": [{"id": 2, "available": False}]}, "timeSignature": {"counter": 500}}
    )
    await hass.async_block_till_done()
    # short hiccup: light stays usable, diagnostic sensor shows the truth
    assert hass.states.get(plain).state == STATE_OFF
    assert hass.states.get(reach).state == STATE_OFF
    import time as _time

    real = _time.monotonic()
    with _patch("custom_components.lunatone_dali.coordinator.time.monotonic", return_value=real + 200):
        coord.async_update_listeners()
        await hass.async_block_till_done()
        assert hass.states.get(plain).state == STATE_UNAVAILABLE
    coord.api._test_on_message(
        {"type": "devices", "data": {"devices": [{"id": 2, "available": True}]}, "timeSignature": {"counter": 501}}
    )
    await hass.async_block_till_done()
    assert hass.states.get(plain).state == STATE_OFF


async def test_push_button_learning(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    await _setup(hass, mock_entry)
    coord = mock_entry.runtime_data
    events = []
    hass.bus.async_listen("lunatone_dali_input", events.append)
    frame = (5 << 17) | (1 << 10) | 0b10  # A5, push button, short press
    coord.api._test_on_message(
        {
            "type": "daliMonitor",
            "data": {"bits": 24, "line": 0, "data": [frame >> 16, (frame >> 8) & 255, frame & 255], "externalSource": True},
        }
    )
    await hass.async_block_till_done()
    assert "0_5_t1" in coord.inputs
    eid = _eid(hass, "event", f"{UID}_input_0_5_t1")
    assert eid is not None
    assert events and events[0].data["type"] == "short_press"
    # second event updates the event entity
    coord.api._test_on_message(
        {
            "type": "daliMonitor",
            "data": {"bits": 24, "line": 0, "data": [frame >> 16, (frame >> 8) & 255, frame & 255], "externalSource": True},
        }
    )
    await hass.async_block_till_done()
    assert hass.states.get(eid).attributes["event_type"] == "short_press"


async def test_unload(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    await _setup(hass, mock_entry)
    assert await hass.config_entries.async_unload(mock_entry.entry_id)
    await hass.async_block_till_done()
