"""DALI-2 IoT Manager integration (gateway: Lunatone DALI-2 IoT)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LunatoneApi, LunatoneError
from .const import DOMAIN
from .coordinator import LunatoneCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type LunatoneConfigEntry = ConfigEntry[LunatoneCoordinator]

ATTR_ENTRY_ID = "config_entry_id"

SCAN_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional("new_installation", default=False): cv.boolean,
        vol.Optional("no_addressing", default=False): cv.boolean,
        vol.Optional("lines", default=[]): vol.All(cv.ensure_list, [vol.Coerce(int)]),
    }
)
DALI16_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Optional("line", default=0): vol.Coerce(int),
        vol.Required("address"): vol.All(vol.Coerce(int), vol.Range(0, 255)),
        vol.Required("command"): vol.All(vol.Coerce(int), vol.Range(0, 255)),
    }
)
DALI24_SCHEMA = DALI16_SCHEMA.extend(
    {vol.Required("instance"): vol.All(vol.Coerce(int), vol.Range(0, 255))}
)
ENTRY_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): cv.string})


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register domain services."""

    def _coordinator(call: ServiceCall) -> LunatoneCoordinator:
        entry_id = call.data.get(ATTR_ENTRY_ID)
        entries = [
            e
            for e in hass.config_entries.async_loaded_entries(DOMAIN)
            if entry_id is None or e.entry_id == entry_id
        ]
        if not entries:
            raise HomeAssistantError("No loaded Lunatone DALI-2 IoT gateway found")
        return entries[0].runtime_data

    async def start_scan(call: ServiceCall) -> ServiceResponse:
        coord = _coordinator(call)
        try:
            return await coord.api.start_scan(
                call.data["new_installation"], call.data["no_addressing"], call.data["lines"]
            )
        except LunatoneError as err:
            raise HomeAssistantError(str(err)) from err

    async def send_dali16(call: ServiceCall) -> ServiceResponse:
        coord = _coordinator(call)
        try:
            answer = await coord.api.send_dali16(
                call.data["line"],
                [{"address": call.data["address"], "command": call.data["command"]}],
            )
        except LunatoneError as err:
            raise HomeAssistantError(str(err)) from err
        return {"response": answer}

    async def send_dali24(call: ServiceCall) -> ServiceResponse:
        coord = _coordinator(call)
        try:
            answer = await coord.api.send_dali24(
                call.data["line"],
                [
                    {
                        "address": call.data["address"],
                        "instance": call.data["instance"],
                        "command": call.data["command"],
                    }
                ],
            )
        except LunatoneError as err:
            raise HomeAssistantError(str(err)) from err
        return {"response": answer}

    async def refresh(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await coord.async_refresh_extras()
        await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "start_scan", start_scan, SCAN_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, "send_dali16", send_dali16, DALI16_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, "send_dali24", send_dali24, DALI24_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(DOMAIN, "refresh", refresh, ENTRY_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LunatoneConfigEntry) -> bool:
    """Set up a gateway from a config entry."""
    api = LunatoneApi(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = LunatoneCoordinator(hass, entry, api)
    await coordinator.async_load_inputs()
    await coordinator.async_config_entry_first_refresh()
    if coordinator.data is None:
        raise ConfigEntryNotReady
    entry.runtime_data = coordinator
    # register the hub first so child devices can reference it
    from .entity import gateway_device_info

    gateway = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **gateway_device_info(coordinator)
    )
    coordinator.gateway_device_id = gateway.id
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_websocket()
    coordinator.start_bus_tasks()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: LunatoneConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LunatoneConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = getattr(entry, "runtime_data", None)
    if unloaded and coordinator is not None:
        await coordinator.async_shutdown()
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: LunatoneConfigEntry, device_entry: Any
) -> bool:
    """Allow removing stale devices (e.g. learned inputs) from the UI."""
    coord = entry.runtime_data
    for domain, ident in device_entry.identifiers:
        if domain != DOMAIN:
            continue
        if ident == coord.uid:
            return False
        prefix = f"{coord.uid}_input_"
        if ident.startswith(prefix):
            addr = ident[len(prefix):]
            for key in [k for k, m in coord.inputs.items() if coord.input_device_key(m) == addr]:
                coord.remove_input(key)
            return True
        # DALI gear still present on the gateway → keep
        for dev in coord.data.devices.values():
            if ident == f"{coord.uid}_{coord.device_key(dev)}":
                return False
    return True
