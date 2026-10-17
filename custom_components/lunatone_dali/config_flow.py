"""Config flow for the Lunatone DALI-2 IoT integration."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:  # HA >= 2025.1
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo
except ImportError:  # pragma: no cover
    from homeassistant.components.hassio import HassioServiceInfo  # type: ignore[no-redef]

from .api import LunatoneApi, LunatoneError
from .const import (
    CONF_DEFAULT_TRANSITION,
    CONF_EXPOSE_BROADCAST,
    CONF_EXPOSE_GROUPS,
    CONF_LEARN_INPUTS,
    CONF_MAX_KELVIN,
    CONF_MIN_KELVIN,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _probe(hass: HomeAssistant, host: str) -> dict[str, Any]:
    """Return /info of a gateway or raise LunatoneError."""
    api = LunatoneApi(async_get_clientsession(hass), host)
    info = await api.info()
    if not isinstance(info, dict) or "uid" not in info or "descriptor" not in info:
        raise LunatoneError("Not a Lunatone DALI-2 IoT gateway")
    return info


async def async_scan_network(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Probe the local /24 networks for DALI-2 IoT gateways."""
    candidates: set[str] = set()
    try:
        from homeassistant.components import network

        adapters = await network.async_get_adapters(hass)
        for adapter in adapters:
            if not adapter.get("enabled"):
                continue
            for ip in adapter.get("ipv4", []):
                addr = ipaddress.ip_address(ip["address"])
                if addr.is_loopback or addr.is_link_local:
                    continue
                prefix = max(int(ip.get("network_prefix", 24)), 24)
                net = ipaddress.ip_network(f"{addr}/{prefix}", strict=False)
                candidates.update(str(h) for h in net.hosts() if h != addr)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not enumerate network adapters: %s", err)
    session = async_get_clientsession(hass)
    sem = asyncio.Semaphore(64)
    found: dict[str, dict[str, Any]] = {}

    async def check(host: str) -> None:
        async with sem:
            try:
                async with session.get(
                    f"http://{host}/info", timeout=aiohttp.ClientTimeout(total=2)
                ) as resp:
                    if resp.status != 200:
                        return
                    info = await resp.json(content_type=None)
            except Exception:  # noqa: BLE001
                return
            if isinstance(info, dict) and "uid" in info and "descriptor" in info:
                found[host] = info

    await asyncio.gather(*(check(h) for h in candidates))
    return found


class LunatoneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._info: dict[str, Any] = {}
        self._found: dict[str, dict[str, Any]] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LunatoneOptionsFlow()

    async def _create(self) -> ConfigFlowResult:
        await self.async_set_unique_id(self._info["uid"])
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
        return self.async_create_entry(
            title=self._info.get("name") or "DALI-2 IoT",
            data={CONF_HOST: self._host},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=["manual", "scan"])

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                self._info = await _probe(self.hass, host)
            except LunatoneError:
                errors["base"] = "cannot_connect"
            else:
                self._host = host
                return await self._create()
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=self._host or ""): str}),
            errors=errors,
        )

    async def async_step_scan(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self._found:
            found = await async_scan_network(self.hass)
            configured = {e.unique_id for e in self._async_current_entries()}
            self._found = {h: i for h, i in found.items() if i.get("uid") not in configured}
            if not self._found:
                return self.async_abort(reason="no_devices_found")
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._info = self._found[self._host]
            return await self._create()
        options = [
            selector.SelectOptionDict(
                value=h, label=f"{i.get('name', 'DALI-2 IoT')} – {h} ({i.get('version', '')})"
            )
            for h, i in self._found.items()
        ]
        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        """Discovery by the Lunatone DALI-2 IoT Manager add-on."""
        host = discovery_info.config.get("host")
        if not host:
            return self.async_abort(reason="cannot_connect")
        try:
            self._info = await _probe(self.hass, host)
        except LunatoneError:
            return self.async_abort(reason="cannot_connect")
        self._host = host
        await self.async_set_unique_id(self._info["uid"])
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self.context["title_placeholders"] = {"name": self._info.get("name", "DALI-2 IoT")}
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self._create()
        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={"name": self._info.get("name", "DALI-2 IoT"), "host": self._host or ""},
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                info = await _probe(self.hass, host)
            except LunatoneError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["uid"])
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates={CONF_HOST: host})
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str}),
            errors=errors,
        )


class LunatoneOptionsFlow(OptionsFlow):
    """Options for a gateway."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(CONF_EXPOSE_GROUPS, default=opts.get(CONF_EXPOSE_GROUPS, True)): bool,
                vol.Optional(CONF_EXPOSE_BROADCAST, default=opts.get(CONF_EXPOSE_BROADCAST, False)): bool,
                vol.Optional(CONF_LEARN_INPUTS, default=opts.get(CONF_LEARN_INPUTS, True)): bool,
                vol.Optional(
                    CONF_DEFAULT_TRANSITION, default=opts.get(CONF_DEFAULT_TRANSITION, 0)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=60, step=0.1, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_MIN_KELVIN, default=opts.get(CONF_MIN_KELVIN, DEFAULT_MIN_KELVIN)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1000, max=10000, step=50, unit_of_measurement="K", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_MAX_KELVIN, default=opts.get(CONF_MAX_KELVIN, DEFAULT_MAX_KELVIN)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1000, max=20000, step=50, unit_of_measurement="K", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=3600, step=5, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
