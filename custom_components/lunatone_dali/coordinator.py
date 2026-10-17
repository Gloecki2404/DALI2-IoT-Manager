"""Data coordinator for the Lunatone DALI-2 IoT gateway (websocket push + polling)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LunatoneApi,
    LunatoneConnectionError,
    LunatoneError,
    LunatoneNotSupported,
    deep_merge,
)
from .const import (
    CONF_LEARN_INPUTS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DISCONNECTED_SCAN_INTERVAL,
    DOMAIN,
    DT_DIAGNOSTICS,
    DT_ENERGY,
    EVENT_DALI_INPUT,
    EXTRAS_INTERVAL,
    SIGNAL_INPUT_EVENT,
    SIGNAL_NEW_INPUT,
    STORAGE_VERSION,
)
from .dali_decode import decode_event

_LOGGER = logging.getLogger(__name__)

# The gateway sometimes flags a gear as unreachable for ~1 min after a single missed
# status query. Lights only become unavailable after this grace period.
UNAVAILABLE_GRACE = 120


@dataclass
class LunatoneData:
    """Snapshot of the gateway state."""

    info: dict[str, Any] = field(default_factory=dict)
    devices: dict[int, dict[str, Any]] = field(default_factory=dict)
    zones: dict[int, dict[str, Any]] = field(default_factory=dict)
    sensors: dict[int, dict[str, Any]] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    scan: dict[str, Any] = field(default_factory=dict)
    automations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    energy: dict[int, dict[str, Any]] = field(default_factory=dict)
    diagnostics: dict[int, dict[str, Any]] = field(default_factory=dict)
    lines: dict[int, dict[str, Any]] = field(default_factory=dict)


def _normalize_device(dev: dict[str, Any]) -> dict[str, Any]:
    """Websocket messages call the unaddressed flag ``shortAddress``."""
    status = dev.get("status")
    if isinstance(status, dict) and "shortAddress" in status:
        status.setdefault("isUnaddressed", status.pop("shortAddress"))
    return dev


class LunatoneCoordinator(DataUpdateCoordinator[LunatoneData]):
    """Keeps the gateway state in sync."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: LunatoneApi) -> None:
        self._poll_interval = timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {api.host}",
            update_interval=timedelta(seconds=DISCONNECTED_SCAN_INTERVAL),
        )
        self.api = api
        self.uid: str = entry.unique_id or entry.entry_id
        self.ws_connected = False
        self._stop = asyncio.Event()
        self._last_counter: int | None = None
        self._refresh_pending = False
        self._unsupported_energy: set[int] = set()
        self._unsupported_diag: set[int] = set()
        self._extras_ts = 0.0
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{self.uid}.inputs"
        )
        self.inputs: dict[str, dict[str, Any]] = {}
        self.gateway_device_id: str | None = None
        # kelvin values sent to lights; the gateway does not always report them back
        self.assumed_kelvin: dict[str, tuple[int, float | None]] = {}
        self._unavail_since: dict[int, float] = {}
        self._seen_available: set[int] = set()

    # ------------------------------------------------------------ lifecycle
    async def async_load_inputs(self) -> None:
        data = await self._store.async_load() or {}
        self.inputs = data.get("inputs", {})

    @callback
    def _save_inputs(self) -> None:
        self._store.async_delay_save(lambda: {"inputs": self.inputs}, 5)

    def start_websocket(self) -> None:
        self.config_entry.async_create_background_task(
            self.hass,
            self.api.listen(self._on_ws_message, self._on_ws_state, self._stop),
            name=f"{DOMAIN}_websocket_{self.uid}",
        )

    async def async_shutdown(self) -> None:
        self._stop.set()
        await super().async_shutdown()

    # --------------------------------------------------------------- polling
    async def _async_update_data(self) -> LunatoneData:
        data = self.data if self.data is not None else LunatoneData()
        try:
            info = await self.api.info()
            devices = await self.api.devices()
            zones = await self.api.zones()
            sensors = await self.api.sensors()
        except LunatoneConnectionError as err:
            raise UpdateFailed(f"Gateway not reachable: {err}") from err
        except LunatoneError as err:
            raise UpdateFailed(str(err)) from err

        data.info = info or {}
        data.devices = {d["id"]: _normalize_device(d) for d in devices}
        data.zones = {z["id"]: z for z in zones}
        data.sensors = {s["id"]: s for s in sensors}
        data.lines = {int(k): v for k, v in (data.info.get("lines") or {}).items()}
        self._track_availability(data)

        for coro, attr in (
            (self.api.settings(), "settings"),
            (self.api.scan(), "scan"),
            (self.api.automations(), "automations"),
        ):
            try:
                setattr(data, attr, await coro or {})
            except LunatoneError as err:
                _LOGGER.debug("Could not read %s: %s", attr, err)

        if time.monotonic() - self._extras_ts > EXTRAS_INTERVAL or not self._extras_ts:
            self._extras_ts = time.monotonic()
            await self._update_extras(data)
        return data

    async def _update_extras(self, data: LunatoneData) -> None:
        """Energy reporting (DT51) and diagnostics (DT52), queried over DALI."""
        for dev_id, dev in data.devices.items():
            types = dev.get("daliTypes") or []
            if not dev.get("available", True):
                continue
            if DT_ENERGY in types and dev_id not in self._unsupported_energy:
                try:
                    data.energy[dev_id] = await self.api.energy(dev_id)
                except LunatoneNotSupported:
                    self._unsupported_energy.add(dev_id)
                except LunatoneError as err:
                    _LOGGER.debug("Energy data for %s failed: %s", dev_id, err)
            if DT_DIAGNOSTICS in types and dev_id not in self._unsupported_diag:
                try:
                    data.diagnostics[dev_id] = await self.api.diagnostics(dev_id)
                except LunatoneNotSupported:
                    self._unsupported_diag.add(dev_id)
                except LunatoneError as err:
                    _LOGGER.debug("Diagnostics for %s failed: %s", dev_id, err)

    async def async_refresh_extras(self) -> None:
        if self.data is None:
            return
        await self._update_extras(self.data)
        self.async_update_listeners()

    # ------------------------------------------------------------- websocket
    async def _on_ws_state(self, connected: bool) -> None:
        if connected == self.ws_connected:
            return
        self.ws_connected = connected
        self.update_interval = (
            self._poll_interval
            if connected
            else timedelta(seconds=DISCONNECTED_SCAN_INTERVAL)
        )
        if connected:
            # resync after (re)connect – we may have missed deltas
            await self.async_request_refresh()
        else:
            self.async_update_listeners()

    @callback
    def _on_ws_message(self, msg: dict[str, Any]) -> None:
        mtype = msg.get("type")
        payload = msg.get("data")
        if mtype == "daliMonitor":
            if isinstance(payload, dict):
                self._handle_monitor(payload)
            return

        sig = msg.get("timeSignature") or {}
        counter = sig.get("counter")
        if counter is not None and counter == self._last_counter:
            return
        self._last_counter = counter

        if self.data is None or not isinstance(payload, dict):
            return
        changed = False
        if mtype == "devices":
            for dev in payload.get("devices", []):
                dev_id = dev.get("id")
                if dev_id in self.data.devices:
                    deep_merge(self.data.devices[dev_id], _normalize_device(dev))
                    changed = True
                    if "available" in dev:
                        self._track_availability(self.data)
                else:
                    self._schedule_resync()
        elif mtype == "zones":
            for zone in payload.get("zones", []):
                zone_id = zone.get("id")
                if zone_id in self.data.zones:
                    deep_merge(self.data.zones[zone_id], zone)
                    changed = True
                else:
                    self._schedule_resync()
        elif mtype == "sensors":
            for sensor in payload.get("sensors", []):
                sid = sensor.get("id")
                if sid in self.data.sensors:
                    deep_merge(self.data.sensors[sid], sensor)
                    changed = True
                else:
                    self._schedule_resync()
        elif mtype == "info":
            self.data.info = payload
            self.data.lines = {int(k): v for k, v in (payload.get("lines") or {}).items()}
            changed = True
        elif mtype == "scan":
            before = self.data.scan.get("status")
            deep_merge(self.data.scan, payload)
            changed = True
            if before != payload.get("status") and payload.get("status") == "done":
                self._schedule_resync()
        else:
            _LOGGER.debug("Unhandled websocket message type %s", mtype)
            self._schedule_resync()
        if changed:
            self.async_update_listeners()

    @callback
    def _schedule_resync(self) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True

        async def _later() -> None:
            await asyncio.sleep(1.5)
            self._refresh_pending = False
            await self.async_request_refresh()

        self.config_entry.async_create_background_task(
            self.hass, _later(), name=f"{DOMAIN}_refresh"
        )

    # --------------------------------------------------------- availability
    @callback
    def _track_availability(self, data: LunatoneData) -> None:
        now = time.monotonic()
        for dev_id, dev in data.devices.items():
            if dev.get("available", True):
                self._unavail_since.pop(dev_id, None)
                self._seen_available.add(dev_id)
            elif dev_id not in self._unavail_since:
                self._unavail_since[dev_id] = now
                if dev_id in self._seen_available:
                    async_call_later(self.hass, UNAVAILABLE_GRACE + 1, self._grace_expired)

    @callback
    def _grace_expired(self, _now: Any) -> None:
        if self.data is not None:
            self.async_update_listeners()

    def device_unavailable(self, dev_id: int) -> bool:
        """True if the gear is unreachable (for longer than the grace period)."""
        since = self._unavail_since.get(dev_id)
        if since is None:
            return False
        if dev_id not in self._seen_available:
            return True  # unreachable since setup
        return time.monotonic() - since >= UNAVAILABLE_GRACE

    # ------------------------------------------------------ input learning
    @callback
    def _handle_monitor(self, frame: dict[str, Any]) -> None:
        if frame.get("bits") != 24:
            return
        evt = decode_event(int(frame.get("line", 0)), list(frame.get("data") or []))
        if evt is None or evt.source_key is None or evt.scheme == "power_cycle":
            return
        key = evt.source_key
        if key not in self.inputs:
            if not self.config_entry.options.get(CONF_LEARN_INPUTS, True):
                return
            self.inputs[key] = {
                "line": evt.line,
                "short_address": evt.short_address,
                "instance_type": evt.instance_type,
                "instance_number": evt.instance_number,
                "kind": evt.kind,
                "first_seen": time.time(),
            }
            self._save_inputs()
            _LOGGER.info("Learned new DALI input %s (%s)", key, evt.kind)
            async_dispatcher_send(self.hass, SIGNAL_NEW_INPUT.format(self.uid), key)
        async_dispatcher_send(
            self.hass, SIGNAL_INPUT_EVENT.format(f"{self.uid}_{key}"), evt
        )
        self.hass.bus.async_fire(
            EVENT_DALI_INPUT,
            {
                "gateway": self.uid,
                "input": key,
                "type": evt.event_type,
                **evt.as_dict(),
            },
        )

    @callback
    def remove_input(self, key: str) -> None:
        if self.inputs.pop(key, None) is not None:
            self._save_inputs()

    # -------------------------------------------------------------- helpers
    async def async_control(
        self, target: str, target_id: int | None, data: dict[str, Any]
    ) -> None:
        """Send a control command and make sure state converges."""
        try:
            await self.api.control(target, target_id, data)
        except LunatoneError as err:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"DALI command failed: {err}") from err
        if not self.ws_connected:
            await self.async_request_refresh()
