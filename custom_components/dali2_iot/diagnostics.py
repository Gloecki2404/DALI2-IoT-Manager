"""Diagnostics download for the Lunatone DALI-2 IoT integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import LunatoneConfigEntry

TO_REDACT = {"uid", "serial", "key", "lat", "lon"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LunatoneConfigEntry
) -> dict[str, Any]:
    coord = entry.runtime_data
    return {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "websocket_connected": coord.ws_connected,
        "learned_inputs": coord.inputs,
        "bus": async_redact_data(
            {
                "identities": coord.identities,
                "failsafe": coord.failsafe,
                "control_devices": coord.control_devices,
                "instance_types": coord.instance_types,
            },
            TO_REDACT,
        ),
        "data": async_redact_data(asdict(coord.data), TO_REDACT) if coord.data else None,
    }
