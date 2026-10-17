"""Device triggers for learned DALI-2 input devices (push buttons, sensors)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_DALI_INPUT
from .dali_decode import BUTTON_EVENT_TYPES, OCCUPANCY_EVENT_TYPES

CONF_SUBTYPE = "subtype"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): str, vol.Required(CONF_SUBTYPE): str}
)


def _inputs_for_device(hass: HomeAssistant, device_id: str) -> list[tuple[str, dict[str, Any]]]:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return []
    result: list[tuple[str, dict[str, Any]]] = []
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coord = entry.runtime_data
        for domain, ident in device.identifiers:
            prefix = f"{coord.uid}_input_"
            if domain != DOMAIN or not ident.startswith(prefix):
                continue
            addr = ident[len(prefix):]  # "<line>_<address>" (or "<line>_x" without address)
            result += [(k, v) for k, v in coord.inputs.items() if coord.input_device_key(v) == addr]
    return result


def _event_types(kind: str) -> list[str]:
    if kind == "push_button":
        return BUTTON_EVENT_TYPES
    if kind == "occupancy_sensor":
        return OCCUPANCY_EVENT_TYPES
    return ["event"]


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []
    for key, meta in _inputs_for_device(hass, device_id):
        for etype in _event_types(meta.get("kind", "")):
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DOMAIN: DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_TYPE: etype,
                    CONF_SUBTYPE: key,
                }
            )
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_DALI_INPUT,
            event_trigger.CONF_EVENT_DATA: {
                "input": config[CONF_SUBTYPE],
                "type": config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
