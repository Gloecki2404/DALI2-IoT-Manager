"""Gateway sensors (DALI-2 part 303/304 etc.) as HA entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.dali2_iot.api import LunatoneApi
from custom_components.dali2_iot.const import DOMAIN

from .conftest import UID

SENSORS = [
    {
        "id": 1,
        "name": "Büro Präsenz",
        "unit": "",
        "type": "occupancy",
        "value": 1,
        "timestamp": "2026-09-27T19:00:00Z",
        "addressType": "dali",
        "daliSensorAddress": {"line": 0, "address": 10, "instanceNumber": 0},
    },
    {
        "id": 2,
        "name": "Büro Helligkeit",
        "unit": "lx",
        "type": "light",
        "value": 412.0,
        "timestamp": "2026-09-27T19:00:00Z",
        "addressType": "dali",
        "daliSensorAddress": {"line": 0, "address": 10, "instanceNumber": 1},
    },
    {
        "id": 3,
        "name": "Temperatur",
        "unit": "°C",
        "type": "temperature",
        "value": 23.4,
        "timestamp": "2026-09-27T19:00:00Z",
        "addressType": "internal",
    },
]


async def test_gateway_sensors(hass: HomeAssistant, mock_entry, gateway_api) -> None:
    with patch.object(LunatoneApi, "sensors", AsyncMock(return_value=SENSORS)):
        mock_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    occ = ent_reg.async_get_entity_id("binary_sensor", DOMAIN, f"{UID}_sensor1")
    lux = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{UID}_sensor2")
    temp = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{UID}_sensor3")
    assert hass.states.get(occ).state == STATE_ON
    assert hass.states.get(occ).attributes["device_class"] == "occupancy"
    assert float(hass.states.get(lux).state) == 412.0
    assert hass.states.get(lux).attributes["device_class"] == "illuminance"
    assert float(hass.states.get(temp).state) == 23.4

    # both DALI sensor instances share one device (line 0, address 10)
    dev_reg = dr.async_get(hass)
    occ_dev = dev_reg.async_get(ent_reg.async_get(occ).device_id)
    lux_dev = dev_reg.async_get(ent_reg.async_get(lux).device_id)
    assert occ_dev.id == lux_dev.id
    assert (DOMAIN, f"{UID}_input_0_10") in occ_dev.identifiers
    gateway = dev_reg.async_get(mock_entry.runtime_data.gateway_device_id)
    assert (DOMAIN, UID) in gateway.identifiers
    assert occ_dev.via_device_id == gateway.id
