"""Light platform – DALI control gear, groups, zones and broadcast."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunatoneConfigEntry
from .const import (
    CONF_DEFAULT_TRANSITION,
    CONF_EXPOSE_BROADCAST,
    CONF_EXPOSE_GROUPS,
    CONF_MAX_KELVIN,
    CONF_MIN_KELVIN,
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
)
from .bus import MASK, level_to_pct, pct_to_level
from .coordinator import LunatoneCoordinator
from .entity import LunatoneDeviceEntity, LunatoneEntity, feature_status

GROUP_NAME = re.compile(r"^group (\d+)$")

SERVICE_SCHEMAS: dict[str, dict[Any, Any]] = {
    "recall_scene": {
        vol.Required("scene"): vol.All(vol.Coerce(int), vol.Range(0, 15)),
        vol.Optional("transition"): vol.All(vol.Coerce(float), vol.Range(0, 3600)),
    },
    "save_scene": {vol.Required("scene"): vol.All(vol.Coerce(int), vol.Range(0, 15))},
    "dim_up": {vol.Optional("steps", default=1): vol.All(vol.Coerce(int), vol.Range(1, 5))},
    "dim_down": {vol.Optional("steps", default=1): vol.All(vol.Coerce(int), vol.Range(1, 5))},
    "goto_last_active": {
        vol.Optional("transition"): vol.All(vol.Coerce(float), vol.Range(0, 3600)),
    },
    "set_fade_time": {vol.Required("fade_time"): vol.All(vol.Coerce(float), vol.Range(0, 16 * 60))},
    "set_fade_rate": {vol.Required("fade_rate"): vol.All(vol.Coerce(float), vol.Range(0, 400))},
    "set_color_waf": {
        vol.Required("white"): vol.All(vol.Coerce(float), vol.Range(0, 1)),
        vol.Required("amber"): vol.All(vol.Coerce(float), vol.Range(0, 1)),
        vol.Required("free"): vol.All(vol.Coerce(float), vol.Range(0, 1)),
        vol.Optional("brightness_pct"): vol.All(vol.Coerce(float), vol.Range(0, 100)),
    },
    "send_raw_control": {vol.Required("data"): dict},
    "set_failsafe_levels": {
        vol.Optional("power_on_level"): vol.All(vol.Coerce(float), vol.Range(0, 100)),
        vol.Optional("power_on_last_level", default=False): cv.boolean,
        vol.Optional("system_failure_level"): vol.All(vol.Coerce(float), vol.Range(0, 100)),
        vol.Optional("system_failure_last_level", default=False): cv.boolean,
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunatoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known_devices: set[int] = set()
    known_zones: set[int] = set()

    @callback
    def _add_new() -> None:
        new: list[LightEntity] = []
        for dev_id, dev in coordinator.data.devices.items():
            if dev_id in known_devices:
                continue
            feats = dev.get("features") or {}
            if "switchable" in feats or "dimmable" in feats:
                known_devices.add(dev_id)
                new.append(DaliDeviceLight(coordinator, dev_id))
        for zone_id, zone in coordinator.data.zones.items():
            if zone_id in known_zones or not zone.get("features"):
                continue
            known_zones.add(zone_id)
            new.append(DaliZoneLight(coordinator, zone_id))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))

    platform = entity_platform.async_get_current_platform()
    for name, schema in SERVICE_SCHEMAS.items():
        platform.async_register_entity_service(name, schema, f"async_service_{name}")


def _pct(brightness: int) -> float:
    return round(max(0.0, min(100.0, brightness * 100 / 255)), 2)


class _DaliLightMixin:
    """Shared state/command logic for lights backed by a features dict."""

    coordinator: LunatoneCoordinator
    features: dict[str, Any]
    unique_id: str | None
    _target: str
    _target_id: int | None
    _last_mode: ColorMode | None = None

    # ------------------------------------------------------------ capability
    @property
    def _has(self) -> set[str]:
        return set(self.features)

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        has = self._has
        modes: set[ColorMode] = set()
        if has & {"colorKelvin", "dimmableKelvin"}:
            modes.add(ColorMode.COLOR_TEMP)
        if has & {"colorRGB", "dimmableRGB"}:
            modes.add(ColorMode.RGB)
        if has & {"colorXY", "dimmableXY"}:
            modes.add(ColorMode.XY)
        if modes:
            return modes
        if "dimmable" in has:
            return {ColorMode.BRIGHTNESS}
        return {ColorMode.ONOFF}

    @property
    def color_mode(self) -> ColorMode:
        modes = self.supported_color_modes
        if self._last_mode in modes:
            return self._last_mode  # type: ignore[return-value]
        for mode in (ColorMode.COLOR_TEMP, ColorMode.RGB, ColorMode.XY, ColorMode.BRIGHTNESS):
            if mode in modes:
                return mode
        return ColorMode.ONOFF

    @property
    def supported_features(self) -> LightEntityFeature:
        if self._has & {"dimmableWithFade", "colorKelvinWithFade", "colorRGBWithFade"}:
            return LightEntityFeature.TRANSITION
        return LightEntityFeature(0)

    @property
    def min_color_temp_kelvin(self) -> int:
        return int(self.coordinator.config_entry.options.get(CONF_MIN_KELVIN, DEFAULT_MIN_KELVIN))

    @property
    def max_color_temp_kelvin(self) -> int:
        return int(self.coordinator.config_entry.options.get(CONF_MAX_KELVIN, DEFAULT_MAX_KELVIN))

    # ----------------------------------------------------------------- state
    @property
    def is_on(self) -> bool | None:
        feats = self.features
        switch = feature_status(feats, "switchable")
        if switch is not None:
            return bool(switch)
        level = feature_status(feats, "dimmable")
        return None if level is None else level > 0

    @property
    def brightness(self) -> int | None:
        level = feature_status(self.features, "dimmable")
        if level is None:
            dk = feature_status(self.features, "dimmableKelvin")
            level = dk.get("dimmable") if isinstance(dk, dict) else None
        if level is None:
            return None
        return max(1, round(level * 255 / 100)) if level > 0 else 0

    def _reported_kelvin(self) -> int | None:
        reported = feature_status(self.features, "colorKelvin")
        if reported is None:
            dk = feature_status(self.features, "dimmableKelvin")
            reported = dk.get("kelvin") if isinstance(dk, dict) else None
        return reported

    @property
    def color_temp_kelvin(self) -> int | None:
        reported = self._reported_kelvin()
        assumed = self.coordinator.assumed_kelvin.get(self.unique_id or "")
        if assumed:
            value, reported_then = assumed
            # keep the commanded value as long as the gateway keeps reporting the
            # old value (many DT8 gear do not update the gateway's colour cache)
            if reported == reported_then:
                return int(value)
            self.coordinator.assumed_kelvin.pop(self.unique_id or "", None)
        return int(reported) if reported else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        rgb = feature_status(self.features, "colorRGB")
        if not isinstance(rgb, dict) or rgb.get("r") is None:
            return None
        return tuple(round((rgb.get(c) or 0) * 255) for c in ("r", "g", "b"))  # type: ignore[return-value]

    @property
    def xy_color(self) -> tuple[float, float] | None:
        xy = feature_status(self.features, "colorXY")
        if not isinstance(xy, dict) or xy.get("x") is None:
            return None
        return (xy["x"], xy["y"])

    # -------------------------------------------------------------- commands
    async def _send(self, data: dict[str, Any]) -> None:
        # DALI has no per-command fade: "*WithFade" permanently changes the fade time of
        # the gear. Restore the configured value afterwards (a running fade keeps going).
        stored_fade = feature_status(self.features, "fadeTime")
        fades = [
            v.get("fadeTime")
            for k, v in data.items()
            if k.endswith("WithFade") and isinstance(v, dict)
        ]
        await self.coordinator.async_control(self._target, self._target_id, data)
        if (
            fades
            and isinstance(stored_fade, (int, float))
            and "fadeTime" in self._has
            and any(abs(float(f or 0) - stored_fade) > 0.05 for f in fades)
        ):
            await self.coordinator.async_control(
                self._target, self._target_id, {"fadeTime": stored_fade}
            )

    def _transition(self, kwargs: dict[str, Any]) -> float | None:
        if ATTR_TRANSITION in kwargs:
            return float(kwargs[ATTR_TRANSITION])
        default = self.coordinator.config_entry.options.get(CONF_DEFAULT_TRANSITION)
        return float(default) if default else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        has = self._has
        fade = self._transition(kwargs)
        use_fade = fade is not None and LightEntityFeature.TRANSITION in self.supported_features
        pct = _pct(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else None
        sent_level = False

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            self._last_mode = ColorMode.COLOR_TEMP
            reported = self._reported_kelvin()
            self.coordinator.assumed_kelvin[self.unique_id or ""] = (kelvin, reported)
            if use_fade and "colorKelvinWithFade" in has:
                await self._send({"colorKelvinWithFade": {"color": kelvin, "fadeTime": fade}})
            elif pct is not None and "dimmableKelvin" in has and not use_fade:
                await self._send({"dimmableKelvin": {"dimmable": pct, "kelvin": kelvin}})
                sent_level = True
            else:
                await self._send({"colorKelvin": kelvin})
        elif ATTR_RGB_COLOR in kwargs:
            r, g, b = (c / 255 for c in kwargs[ATTR_RGB_COLOR])
            self._last_mode = ColorMode.RGB
            if use_fade and "colorRGBWithFade" in has:
                await self._send({"colorRGBWithFade": {"color": {"r": r, "g": g, "b": b}, "fadeTime": fade}})
            elif pct is not None and "dimmableRGB" in has and not use_fade:
                await self._send({"dimmableRGB": {"r": r, "g": g, "b": b, "dimmable": pct}})
                sent_level = True
            else:
                await self._send({"colorRGB": {"r": r, "g": g, "b": b}})
        elif ATTR_XY_COLOR in kwargs:
            x, y = kwargs[ATTR_XY_COLOR]
            self._last_mode = ColorMode.XY
            if use_fade and "colorXYWithFade" in has:
                await self._send({"colorXYWithFade": {"color": {"x": x, "y": y}, "fadeTime": fade}})
            elif pct is not None and "dimmableXY" in has and not use_fade:
                await self._send({"dimmableXY": {"x": x, "y": y, "dimmable": pct}})
                sent_level = True
            else:
                await self._send({"colorXY": {"x": x, "y": y}})

        if sent_level:
            return
        if pct is not None:
            if use_fade and "dimmableWithFade" in has:
                await self._send({"dimmableWithFade": {"dimValue": pct, "fadeTime": fade}})
            elif "dimmable" in has:
                await self._send({"dimmable": pct})
            else:
                await self._send({"switchable": pct > 0})
            return
        if self.is_on:
            return  # already on (colour change only)
        if use_fade and "gotoLastActiveWithFade" in has:
            await self._send({"gotoLastActiveWithFade": {"fadeTime": fade}})
        elif "gotoLastActive" in has:
            await self._send({"gotoLastActive": True})
        else:
            await self._send({"switchable": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        fade = self._transition(kwargs)
        if fade is not None and "dimmableWithFade" in self._has:
            await self._send({"dimmableWithFade": {"dimValue": 0, "fadeTime": fade}})
        elif "switchable" in self._has:
            await self._send({"switchable": False})
        else:
            await self._send({"dimmable": 0})

    # -------------------------------------------------------------- services
    async def async_service_recall_scene(self, scene: int, transition: float | None = None) -> None:
        if transition is not None and "sceneWithFade" in self._has:
            await self._send({"sceneWithFade": {"scene": scene, "fadeTime": transition}})
        else:
            await self._send({"scene": scene})

    async def async_service_save_scene(self, scene: int) -> None:
        await self._send({"saveToScene": scene})

    async def async_service_dim_up(self, steps: int = 1) -> None:
        await self._send({"dimUp": steps})

    async def async_service_dim_down(self, steps: int = 1) -> None:
        await self._send({"dimDown": steps})

    async def async_service_goto_last_active(self, transition: float | None = None) -> None:
        if transition is not None and "gotoLastActiveWithFade" in self._has:
            await self._send({"gotoLastActiveWithFade": {"fadeTime": transition}})
        else:
            await self._send({"gotoLastActive": True})

    async def async_service_set_fade_time(self, fade_time: float) -> None:
        await self._send({"fadeTime": fade_time})

    async def async_service_set_fade_rate(self, fade_rate: float) -> None:
        await self._send({"fadeRate": fade_rate})

    async def async_service_set_color_waf(
        self, white: float, amber: float, free: float, brightness_pct: float | None = None
    ) -> None:
        if brightness_pct is not None:
            await self._send({"dimmableWAF": {"w": white, "a": amber, "f": free, "dimmable": brightness_pct}})
        else:
            await self._send({"colorWAF": {"w": white, "a": amber, "f": free}})

    async def async_service_send_raw_control(self, data: dict[str, Any]) -> None:
        await self._send(data)

    async def async_service_set_failsafe_levels(self, **kwargs: Any) -> None:
        raise HomeAssistantError("Fail-safe levels can only be set for single DALI lights")


class DaliDeviceLight(LunatoneDeviceEntity, _DaliLightMixin, LightEntity):
    """A single DALI control gear."""

    _attr_name = None  # use the device name

    def __init__(self, coordinator: LunatoneCoordinator, device_id: int) -> None:
        LunatoneDeviceEntity.__init__(self, coordinator, device_id, "light")
        self._target = "device"
        self._target_id = device_id

    @property
    def features(self) -> dict[str, Any]:
        return self.device.get("features") or {}

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.device_unavailable(self.device_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        dev = self.device
        feats = self.features
        status = dev.get("status") or {}
        levels = self.coordinator.failsafe_levels(dev)
        return {
            "dali_line": dev.get("line"),
            "dali_address": dev.get("address"),
            "dali_groups": dev.get("groups"),
            "dali_types": dev.get("daliTypes"),
            "gateway_device_id": dev.get("id"),
            "fade_time": feature_status(feats, "fadeTime"),
            "fade_rate": feature_status(feats, "fadeRate"),
            "lamp_on": status.get("lampOn"),
            "fade_running": status.get("fadeRunning"),
            "status_raw": status.get("raw"),
            # behaviour without the gateway (stored in the gear itself)
            "power_on_level": level_to_pct(levels.get("power_on_level")),
            "system_failure_level": level_to_pct(levels.get("system_failure_level")),
        }

    async def async_service_set_failsafe_levels(
        self,
        power_on_level: float | None = None,
        power_on_last_level: bool = False,
        system_failure_level: float | None = None,
        system_failure_last_level: bool = False,
    ) -> None:
        power_on = MASK if power_on_last_level else None if power_on_level is None else pct_to_level(power_on_level)
        failure = (
            MASK
            if system_failure_last_level
            else None
            if system_failure_level is None
            else pct_to_level(system_failure_level)
        )
        if power_on is None and failure is None:
            raise HomeAssistantError("Nothing to set")
        await self.coordinator.async_set_failsafe(self.device_id, power_on, failure)


class DaliZoneLight(LunatoneEntity, _DaliLightMixin, LightEntity):
    """A zone on the gateway: broadcast, a DALI group or a user defined zone."""

    def __init__(self, coordinator: LunatoneCoordinator, zone_id: int) -> None:
        LunatoneEntity.__init__(self, coordinator, f"zone{zone_id}")
        self.zone_id = zone_id
        self._target = "zone"
        self._target_id = zone_id
        zone = self.zone
        targets = zone.get("targets") or []
        name = zone.get("name") or f"Zone {zone_id}"
        opts = coordinator.config_entry.options
        if len(targets) == 1 and targets[0].get("type") == "broadcast":
            self._attr_translation_key = "broadcast"
            self._attr_entity_registry_enabled_default = opts.get(CONF_EXPOSE_BROADCAST, False)
        elif (m := GROUP_NAME.match(name)) and len(targets) == 1 and targets[0].get("type") == "group":
            self._attr_translation_key = "group"
            self._attr_translation_placeholders = {"number": m.group(1)}
            self._attr_entity_registry_enabled_default = opts.get(CONF_EXPOSE_GROUPS, True)
        else:
            self._attr_name = name

    @property
    def zone(self) -> dict[str, Any]:
        return self.coordinator.data.zones.get(self.zone_id, {}) if self.coordinator.data else {}

    @property
    def features(self) -> dict[str, Any]:
        return self.zone.get("features") or {}

    @property
    def available(self) -> bool:
        return super().available and self.zone_id in self.coordinator.data.zones

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        targets = self.zone.get("targets") or []
        members: list[str] = []
        for tgt in targets:
            if tgt.get("type") == "group":
                members += [
                    d.get("name", "")
                    for d in self.coordinator.data.devices.values()
                    if tgt.get("id") in (d.get("groups") or [])
                ]
            elif tgt.get("type") == "device":
                dev = self.coordinator.data.devices.get(tgt.get("id"), {})
                members.append(dev.get("name", ""))
        return {"zone_id": self.zone_id, "targets": targets, "members": members}
