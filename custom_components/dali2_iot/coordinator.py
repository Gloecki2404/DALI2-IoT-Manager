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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import bus
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
from .dali_decode import classify_event, decode_event

_LOGGER = logging.getLogger(__name__)

# The gateway sometimes flags a gear as unreachable for ~1 min after a single missed
# status query. Lights only become unavailable after this grace period.
UNAVAILABLE_GRACE = 120

# Instance types learned as HA events: push buttons (301) and occupancy (303).
# Measured values (light level, positions) arrive as gateway sensors instead –
# a light sensor reports about once per second and would flood the recorder.
LEARNED_INSTANCE_TYPES = {1, 3}
SENSOR_TYPE_BY_INSTANCE = {3: "occupancy", 4: "light"}

# Bus reads (memory bank 0, fail-safe levels, control devices) start a little
# after setup and are repeated at most every IDENTITY_MAX_AGE seconds (plus
# after every DALI scan, which may re-address devices).
STARTUP_DELAY = 10
IDENTITY_MAX_AGE = 600
RESOLVE_RETRY = 300


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
        # raw bus knowledge (identity, fail-safe levels, control devices)
        self._bus_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{self.uid}.bus"
        )
        self._bus_lock = asyncio.Lock()
        self.identities: dict[str, dict[str, Any]] = {}  # address key → bank 0 identity
        self.failsafe: dict[str, dict[str, int | None]] = {}  # address key → levels
        self.control_devices: list[dict[str, Any]] = []
        self.control_scan_ts: float | None = None
        self.instance_types: dict[str, int] = {}  # "line_address_instance" → type
        self._identity_ts = 0.0
        self._duplicate_keys: set[str] = set()
        self._resolving: set[str] = set()
        self._resolve_failed: dict[str, float] = {}
        self._last_occupancy: dict[str, str | None] = {}
        self.occupancy_override: dict[int, bool] = {}

    # ------------------------------------------------------------ lifecycle
    async def async_load_inputs(self) -> None:
        data = await self._store.async_load() or {}
        self.inputs = data.get("inputs", {})
        bus_data = await self._bus_store.async_load() or {}
        self.identities = bus_data.get("identities", {})
        self.failsafe = bus_data.get("failsafe", {})
        self.control_devices = bus_data.get("control_devices", [])
        self.control_scan_ts = bus_data.get("control_scan_ts")
        self.instance_types = bus_data.get("instance_types", {})
        self._identity_ts = bus_data.get("identity_ts", 0.0)
        self._update_duplicates()

    @callback
    def _save_inputs(self) -> None:
        self._store.async_delay_save(lambda: {"inputs": self.inputs}, 5)

    def _bus_data(self) -> dict[str, Any]:
        return {
            "identities": self.identities,
            "failsafe": self.failsafe,
            "control_devices": self.control_devices,
            "control_scan_ts": self.control_scan_ts,
            "instance_types": self.instance_types,
            "identity_ts": self._identity_ts,
        }

    @callback
    def _save_bus(self) -> None:
        self._bus_store.async_delay_save(self._bus_data, 2)

    async def _async_reload(self) -> None:
        """Persist everything first – the reloaded entry reads the stores again."""
        await self._bus_store.async_save(self._bus_data())
        await self._store.async_save({"inputs": self.inputs})
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

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
                    if "value" in sensor:
                        self.occupancy_override.pop(sid, None)
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
                self.config_entry.async_create_background_task(
                    self.hass, self._after_scan(), name=f"{DOMAIN}_after_scan"
                )
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

    # ------------------------------------------------------- device identity
    @staticmethod
    def address_key(dev: dict[str, Any]) -> str:
        return f"l{dev.get('line', 0)}_a{dev.get('address', dev.get('id'))}"

    def device_key(self, dev: dict[str, Any]) -> str:
        """Identity of a control gear: GTIN + identification number (memory bank 0)
        if known and unique, else line + short address. Survives re-addressing."""
        akey = self.address_key(dev)
        key = (self.identities.get(akey) or {}).get("key")
        return key if key and key not in self._duplicate_keys else akey

    def identity(self, dev: dict[str, Any]) -> dict[str, Any]:
        return self.identities.get(self.address_key(dev)) or {}

    def failsafe_levels(self, dev: dict[str, Any]) -> dict[str, int | None]:
        return self.failsafe.get(self.address_key(dev)) or {}

    @callback
    def _update_duplicates(self) -> None:
        seen: set[str] = set()
        dup: set[str] = set()
        for ident in self.identities.values():
            if key := ident.get("key"):
                (dup if key in seen else seen).add(key)
        if dup:
            _LOGGER.warning("DALI gear with identical identification number: %s – using addresses", dup)
        self._duplicate_keys = dup

    def start_bus_tasks(self) -> None:
        self.config_entry.async_create_background_task(
            self.hass, self._initial_bus_reads(), name=f"{DOMAIN}_bus_reads_{self.uid}"
        )

    async def _initial_bus_reads(self) -> None:
        await asyncio.sleep(STARTUP_DELAY)
        await self.async_read_gears()
        if self.control_scan_ts is None:
            await self.async_scan_control_devices()

    async def _after_scan(self) -> None:
        """A scan may assign new short addresses – re-read who is where."""
        await asyncio.sleep(3)
        await self.async_request_refresh()
        await self.async_read_gears(force=True)
        await self.async_scan_control_devices()

    async def async_read_gears(self, force: bool = False) -> None:
        """Read identity + fail-safe levels of all gear (one request per gear)."""
        if self.data is None:
            return
        if not force and time.time() - self._identity_ts < IDENTITY_MAX_AGE:
            return
        async with self._bus_lock:
            before = {dev_id: self.device_key(dev) for dev_id, dev in self.data.devices.items()}
            for dev in list(self.data.devices.values()):
                if not dev.get("available", True) or dev.get("address") is None:
                    continue
                akey = self.address_key(dev)
                try:
                    res = await bus.read_gear(self.api, int(dev.get("line", 0)), int(dev["address"]))
                except LunatoneError as err:
                    _LOGGER.debug("Reading gear %s failed: %s", akey, err)
                    continue
                finally:
                    await asyncio.sleep(bus.PAUSE)
                if res["power_on_level"] is None and res["identity"] is None:
                    continue  # no answer at all – keep what we know
                if res["identity"] is not None:
                    self.identities[akey] = res["identity"]
                else:
                    self.identities.pop(akey, None)  # no memory bank 0
                self.failsafe[akey] = {
                    "power_on_level": res["power_on_level"],
                    "system_failure_level": res["system_failure_level"],
                }
            present = {self.address_key(dev) for dev in self.data.devices.values()}
            for store in (self.identities, self.failsafe):
                for akey in [k for k in store if k not in present]:
                    del store[akey]
            self._identity_ts = time.time()
            self._update_duplicates()
            self._save_bus()
        after = {dev_id: self.device_key(dev) for dev_id, dev in self.data.devices.items()}
        changed = [(before[dev_id], key) for dev_id, key in after.items() if before.get(dev_id, key) != key]
        if changed:
            self._migrate_registry(changed)
            _LOGGER.info("DALI gear identities changed (%s) – reloading", len(changed))
            await self._async_reload()
        else:
            self.async_update_listeners()

    @callback
    def _migrate_registry(self, pairs: list[tuple[str, str]]) -> None:
        """Move devices/entities from address based to identity based unique IDs.

        Only address → identity is migrated: in every other case the physical
        gear behind the address may have changed (re-addressing scan)."""
        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)
        entries = er.async_entries_for_config_entry(ent_reg, self.config_entry.entry_id)
        for old, new in pairs:
            if not old.startswith("l") or new.startswith("l"):
                continue
            old_ident = (DOMAIN, f"{self.uid}_{old}")
            new_ident = (DOMAIN, f"{self.uid}_{new}")
            device = dev_reg.async_get_device(identifiers={old_ident})
            if device is not None and dev_reg.async_get_device(identifiers={new_ident}) is None:
                dev_reg.async_update_device(device.id, new_identifiers={new_ident})
            prefix = f"{self.uid}_{old}_"
            for ent in entries:
                if not ent.unique_id.startswith(prefix):
                    continue
                new_uid = f"{self.uid}_{new}_{ent.unique_id[len(prefix):]}"
                if ent_reg.async_get_entity_id(ent.domain, DOMAIN, new_uid) is None:
                    ent_reg.async_update_entity(ent.entity_id, new_unique_id=new_uid)

    async def async_set_failsafe(
        self, dev_id: int, power_on: int | None = None, system_failure: int | None = None
    ) -> None:
        """Write power-on / system failure level (stored non-volatile in the gear)."""
        dev = self.data.devices.get(dev_id) if self.data else None
        if not dev or dev.get("address") is None:
            raise HomeAssistantError("Unknown DALI device")
        line, short = int(dev.get("line", 0)), int(dev["address"])
        async with self._bus_lock:
            try:
                if power_on is not None:
                    await bus.write_gear_level(self.api, line, short, bus.SET_POWER_ON_LEVEL, power_on)
                if system_failure is not None:
                    await bus.write_gear_level(self.api, line, short, bus.SET_SYSTEM_FAILURE_LEVEL, system_failure)
                res = await bus.read_gear(self.api, line, short)
            except LunatoneError as err:
                raise HomeAssistantError(f"DALI command failed: {err}") from err
        self.failsafe[self.address_key(dev)] = {
            "power_on_level": res["power_on_level"],
            "system_failure_level": res["system_failure_level"],
        }
        self._save_bus()
        self.async_update_listeners()
        if (power_on is not None and res["power_on_level"] != power_on) or (
            system_failure is not None and res["system_failure_level"] != system_failure
        ):
            raise HomeAssistantError("The DALI gear did not confirm the new level")

    # -------------------------------------------------------- control devices
    def control_device(self, line: int, address: Any) -> dict[str, Any] | None:
        return next(
            (d for d in self.control_devices if d.get("line") == line and d.get("address") == address),
            None,
        )

    async def async_scan_control_devices(self) -> list[dict[str, Any]]:
        """Find DALI-2 input devices (IEC 62386-103) and read their setup."""
        if self.data is None:
            return []
        lines = sorted(self.data.lines) or [0]
        async with self._bus_lock:
            try:
                devices = await bus.scan_control_devices(self.api, lines)
            except LunatoneError as err:
                _LOGGER.warning("Searching DALI control devices failed: %s", err)
                return self.control_devices
        self.control_devices = devices
        self.control_scan_ts = time.time()
        for dev in devices:
            for inst in dev.get("instances", []):
                if inst.get("type") is not None:
                    self.instance_types[f"{dev['line']}_{dev['address']}_{inst['number']}"] = inst["type"]
        moved = self._apply_control_devices()
        self._save_bus()
        if moved:
            await self._async_reload()  # inputs got their device address
        else:
            self.async_update_listeners()
        return devices

    @callback
    def _apply_control_devices(self) -> bool:
        """Create event entities for inputs found by the scan (before the first press).

        Returns True if known inputs moved to another device (needs a reload)."""
        counts: dict[str, int] = {}
        for dev in self.control_devices:
            for key, _inst in bus.input_keys(dev):
                counts[key] = counts.get(key, 0) + 1
        learn = self.config_entry.options.get(CONF_LEARN_INPUTS, True)
        new_keys: list[str] = []
        moved = False
        ambiguous: set[str] = set()
        for dev in self.control_devices:
            line, short = dev["line"], dev["address"]
            for key, inst in bus.input_keys(dev):
                if inst.get("type") not in LEARNED_INSTANCE_TYPES or not inst.get("enabled"):
                    continue
                if inst.get("event_filter") == 0:
                    continue  # this instance sends no events at all
                is_ambiguous = counts[key] > 1
                if is_ambiguous:
                    ambiguous.add(key)
                addr = None if is_ambiguous else short
                meta = self.inputs.get(key)
                if meta is None:
                    if not learn:
                        continue
                    self.inputs[key] = {
                        "line": line,
                        "short_address": addr,
                        "device_key": f"{line}_{addr if addr is not None else 'x'}",
                        "instance_type": inst["type"],
                        "instance_number": None if inst.get("event_scheme") == "device" else inst["number"],
                        "kind": inst.get("kind"),
                        "first_seen": time.time(),
                        "source": "scan",
                    }
                    new_keys.append(key)
                elif meta.get("short_address") is None and addr is not None:
                    meta["short_address"] = addr
                    meta["device_key"] = f"{line}_{addr}"
                    moved = True
                if key in self.inputs:
                    self.inputs[key]["ambiguous"] = is_ambiguous
        if ambiguous:
            _LOGGER.warning(
                "DALI inputs %s cannot be told apart by their events – set the event scheme "
                "of these instances to 'device/instance' (e.g. in the DALI-2 IoT Manager add-on)",
                sorted(ambiguous),
            )
        self._save_inputs()
        for key in new_keys:
            async_dispatcher_send(self.hass, SIGNAL_NEW_INPUT.format(self.uid), key)
        return moved

    # ------------------------------------------------------ input learning
    @callback
    def _handle_monitor(self, frame: dict[str, Any]) -> None:
        if frame.get("bits") != 24:
            return
        evt = decode_event(int(frame.get("line", 0)), list(frame.get("data") or []))
        if evt is None or evt.source_key is None or evt.scheme == "power_cycle":
            return
        if evt.instance_type is None and evt.short_address is not None and evt.instance_number is not None:
            # scheme "device/instance" carries no instance type – look it up
            ikey = f"{evt.line}_{evt.short_address}_{evt.instance_number}"
            itype = self.instance_types.get(ikey)
            if itype is None:
                self._resolve_instance_type(ikey, evt)
                return
            evt.instance_type = itype
            classify_event(evt)
        self._process_event(evt)

    @callback
    def _resolve_instance_type(self, ikey: str, evt: Any) -> None:
        if ikey in self._resolving:
            return
        if time.monotonic() - self._resolve_failed.get(ikey, -RESOLVE_RETRY) < RESOLVE_RETRY:
            return
        self._resolving.add(ikey)

        async def _query() -> None:
            try:
                async with self._bus_lock:
                    itype = await bus.query_instance_type(self.api, evt.line, evt.short_address, evt.instance_number)
            except LunatoneError:
                itype = None
            finally:
                self._resolving.discard(ikey)
            if itype is None:
                self._resolve_failed[ikey] = time.monotonic()
                return
            self.instance_types[ikey] = itype
            self._save_bus()
            evt.instance_type = itype
            classify_event(evt)
            self._process_event(evt)  # deliver the first event late instead of never

        self.config_entry.async_create_background_task(
            self.hass, _query(), name=f"{DOMAIN}_instance_type"
        )

    @callback
    def _process_event(self, evt: Any) -> None:
        if evt.instance_type not in LEARNED_INSTANCE_TYPES:
            return
        key = evt.source_key
        if evt.instance_type == 3:
            self._update_gateway_occupancy(evt)
            # sensors repeat their state periodically and report every movement –
            # only state changes become HA events
            if self._last_occupancy.get(key) == evt.event_type:
                return
            self._last_occupancy[key] = evt.event_type
        if key not in self.inputs:
            if not self.config_entry.options.get(CONF_LEARN_INPUTS, True):
                return
            short = evt.short_address
            if short is None:
                short = self._address_from_control_devices(evt)
            if short is None:
                short = self._address_from_sensors(evt)
            self.inputs[key] = {
                "line": evt.line,
                "short_address": short,
                "device_key": f"{evt.line}_{short if short is not None else 'x'}",
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
    def _update_gateway_occupancy(self, evt: Any) -> None:
        """The gateway only updates its occupancy sensors for events that carry the
        device address – keep them current from the events themselves."""
        if self.data is None:
            return
        short = evt.short_address
        if short is None:
            short = self._address_from_control_devices(evt)
        candidates = []
        for sid, sensor in self.data.sensors.items():
            addr = sensor.get("daliSensorAddress") or {}
            if sensor.get("type") != "occupancy" or sensor.get("addressType") != "dali":
                continue
            if addr.get("line") != evt.line:
                continue
            if evt.instance_number is not None and addr.get("instanceNumber") != evt.instance_number:
                continue
            if short is not None and addr.get("address") != short:
                continue
            candidates.append(sid)
        if not candidates or (short is None and len(candidates) > 1):
            return
        occupied = evt.event_type == "occupied"
        changed = False
        for sid in candidates:
            if self.occupancy_override.get(sid) != occupied:
                self.occupancy_override[sid] = occupied
                changed = True
        if changed:
            self.async_update_listeners()

    def _address_from_control_devices(self, evt: Any) -> int | None:
        """Scheme "instance" events: the control device scan knows the sender."""
        matches = {
            dev["address"]
            for dev in self.control_devices
            if dev.get("line") == evt.line
            for inst in dev.get("instances", [])
            if inst.get("type") == evt.instance_type
            and inst.get("number") == evt.instance_number
            and inst.get("event_scheme") == "instance"
        }
        return matches.pop() if len(matches) == 1 else None

    def _address_from_sensors(self, evt: Any) -> int | None:
        """Events in scheme "instance" carry no address – look it up in the gateway's sensor list."""
        stype = SENSOR_TYPE_BY_INSTANCE.get(evt.instance_type)
        if self.data is None or stype is None:
            return None
        matches = {
            (s.get("daliSensorAddress") or {}).get("address")
            for s in self.data.sensors.values()
            if s.get("addressType") == "dali"
            and s.get("type") == stype
            and (s.get("daliSensorAddress") or {}).get("line") == evt.line
            and (s.get("daliSensorAddress") or {}).get("instanceNumber") == evt.instance_number
        }
        return matches.pop() if len(matches) == 1 else None

    @staticmethod
    def input_device_key(meta: dict[str, Any]) -> str:
        if meta.get("device_key"):
            return str(meta["device_key"])
        return f"{meta.get('line', 0)}_{meta.get('short_address')}"

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
