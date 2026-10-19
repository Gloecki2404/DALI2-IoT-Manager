"""Binary sensors – DALI gear status flags, occupancy, gateway state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LunatoneConfigEntry
from .coordinator import LunatoneCoordinator
from .entity import (
    LunatoneDeviceEntity,
    LunatoneEntity,
    LunatoneGatewaySensorEntity,
    input_device_info,
)


@dataclass(frozen=True, kw_only=True)
class StatusDescription(BinarySensorEntityDescription):
    status_key: str


STATUS_SENSORS: tuple[StatusDescription, ...] = (
    StatusDescription(
        key="lamp_failure",
        translation_key="lamp_failure",
        status_key="lampFailure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    StatusDescription(
        key="gear_failure",
        translation_key="gear_failure",
        status_key="controlGearFailure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    StatusDescription(
        key="limit_error",
        translation_key="limit_error",
        status_key="limitError",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    StatusDescription(
        key="power_cycle_seen",
        translation_key="power_cycle_seen",
        status_key="powerCycleSeen",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    StatusDescription(
        key="reset_state",
        translation_key="reset_state",
        status_key="resetState",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    StatusDescription(
        key="lamp_on",
        translation_key="lamp_on",
        status_key="lampOn",
        device_class=BinarySensorDeviceClass.LIGHT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)

DIAG_BOOL_KEYS: dict[str, str] = {
    "controlGearOverallFailureCondition": "diag_gear_overall_failure",
    "controlGearExternalSupplyUndervoltage": "diag_undervoltage",
    "controlGearExternalSupplyOvervoltage": "diag_overvoltage",
    "controlGearOutputPowerLimitation": "diag_power_limitation",
    "controlGearThermalDerating": "diag_gear_thermal_derating",
    "controlGearThermalShutdown": "diag_gear_thermal_shutdown",
    "lightSourceOverallFailureCondition": "diag_light_overall_failure",
    "lightSourceShortCircuit": "diag_short_circuit",
    "lightSourceOpenCircuit": "diag_open_circuit",
    "lightSourceThermalDerating": "diag_light_thermal_derating",
    "lightSourceThermalShutdown": "diag_light_thermal_shutdown",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunatoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    entities: list[BinarySensorEntity] = [GatewayConnectedSensor(coordinator)]
    for line in coordinator.data.lines:
        entities.append(LineProblemSensor(coordinator, line))
    async_add_entities(entities)

    @callback
    def _add_new() -> None:
        new: list[BinarySensorEntity] = []
        data = coordinator.data
        for dev_id in data.devices:
            key = f"dev{dev_id}"
            if key not in known:
                known.add(key)
                new.append(DeviceAvailableSensor(coordinator, dev_id))
                new += [DeviceStatusSensor(coordinator, dev_id, d) for d in STATUS_SENSORS]
        for dev_id, diag in data.diagnostics.items():
            for dkey, tkey in DIAG_BOOL_KEYS.items():
                key = f"diag{dev_id}_{dkey}"
                if key not in known and dkey in diag:
                    known.add(key)
                    new.append(DiagnosticsFlagSensor(coordinator, dev_id, dkey, tkey))
        for sid, sensor in data.sensors.items():
            key = f"sensor{sid}"
            if key not in known and sensor.get("type") == "occupancy":
                known.add(key)
                new.append(OccupancySensor(coordinator, sid))
        for found in coordinator.control_devices:
            key = f"ctrl{found['line']}_{found['address']}"
            if key not in known:
                known.add(key)
                new.append(FailsafeInputSensor(coordinator, found["line"], found["address"]))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class DeviceStatusSensor(LunatoneDeviceEntity, BinarySensorEntity):
    entity_description: StatusDescription

    def __init__(self, coordinator: LunatoneCoordinator, device_id: int, desc: StatusDescription) -> None:
        super().__init__(coordinator, device_id, desc.key)
        self.entity_description = desc

    @property
    def is_on(self) -> bool | None:
        value = (self.device.get("status") or {}).get(self.entity_description.status_key)
        return None if value is None else bool(value)


class DeviceAvailableSensor(LunatoneDeviceEntity, BinarySensorEntity):
    _attr_translation_key = "reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "reachable")

    @property
    def is_on(self) -> bool:
        return bool(self.device.get("available", False))


class DiagnosticsFlagSensor(LunatoneDeviceEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator, device_id: int, dkey: str, tkey: str) -> None:
        super().__init__(coordinator, device_id, tkey)
        self._dkey = dkey
        self._attr_translation_key = tkey

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.diagnostics.get(self.device_id, {}).get(self._dkey)
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        counter = self.coordinator.data.diagnostics.get(self.device_id, {}).get(f"{self._dkey}Counter")
        return {"counter": counter} if counter is not None else {}


class OccupancySensor(LunatoneGatewaySensorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self) -> bool | None:
        override = self.coordinator.occupancy_override.get(self.sensor_id)
        if override is not None:
            return override  # from the sensor's own bus events
        value = self.sensor.get("value")
        return None if value is None else bool(value)


class FailsafeInputSensor(CoordinatorEntity[LunatoneCoordinator], BinarySensorEntity):
    """On when the input device switches lights itself (application controller
    active), i.e. keeps working when the gateway fails."""

    _attr_has_entity_name = True
    _attr_translation_key = "failsafe"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator, line: int, address: int) -> None:
        super().__init__(coordinator)
        self.line = line
        self.address = address
        self._attr_unique_id = f"{coordinator.uid}_input_{line}_{address}_failsafe"
        self._attr_device_info = input_device_info(coordinator, line, address)

    @property
    def found(self) -> dict[str, Any]:
        return self.coordinator.control_device(self.line, self.address) or {}

    @property
    def available(self) -> bool:
        return bool(self.found)

    @property
    def is_on(self) -> bool:
        return bool(self.found.get("app_controller_enabled"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        found = self.found
        return {
            "application_controller_present": found.get("app_controller_present"),
            "events_to_gateway": found.get("events_to_gateway"),
            "quiescent_mode": found.get("quiescent"),
            "gtin": found.get("gtin"),
            "instances": [
                {k: inst.get(k) for k in ("number", "kind", "enabled", "event_scheme")}
                for inst in found.get("instances", [])
            ],
        }


class GatewayConnectedSensor(LunatoneEntity, BinarySensorEntity):
    _attr_translation_key = "websocket"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator) -> None:
        super().__init__(coordinator, "websocket")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.ws_connected


class LineProblemSensor(LunatoneEntity, BinarySensorEntity):
    _attr_translation_key = "line_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator, line: int) -> None:
        super().__init__(coordinator, f"line{line}_problem")
        self.line = line
        self._attr_translation_placeholders = {"line": str(line)}

    @property
    def is_on(self) -> bool | None:
        line = self.coordinator.data.lines.get(self.line)
        if not line:
            return None
        return line.get("lineStatus", "ok") != "ok" or any(
            line.get(k) for k in ("sendBufferFull",)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        line = self.coordinator.data.lines.get(self.line) or {}
        return {k: v for k, v in line.items() if k != "device"}
