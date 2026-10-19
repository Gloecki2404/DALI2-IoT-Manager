"""Base entities for the Lunatone DALI-2 IoT integration."""

from __future__ import annotations

from typing import Any

from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DALI_TYPES, DOMAIN, MANUFACTURER
from .coordinator import LunatoneCoordinator


# HA 2026.8 replaced DeviceInfo.via_device (identifier tuple) by via_device_id
USE_VIA_DEVICE_ID = (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8)


def via_gateway(coordinator: LunatoneCoordinator) -> dict[str, Any]:
    """Link a child device to the gateway device."""
    if USE_VIA_DEVICE_ID:
        return {"via_device_id": coordinator.gateway_device_id} if coordinator.gateway_device_id else {}
    return {"via_device": (DOMAIN, coordinator.uid)}


def gateway_device_info(coordinator: LunatoneCoordinator) -> DeviceInfo:
    info = coordinator.data.info if coordinator.data else {}
    dev = info.get("device") or {}
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.uid)},
        manufacturer=MANUFACTURER,
        name=info.get("name") or "DALI-2 IoT",
        model="DALI-2 IoT",
        model_id=str(dev.get("articleNumber") or "") or None,
        serial_number=str(dev.get("serial") or "") or None,
        sw_version=(info.get("version") or "").lstrip("v") or None,
        hw_version=f"PCB {dev['pcb']}" if dev.get("pcb") else None,
        configuration_url=coordinator.api.base_url,
    )


class LunatoneEntity(CoordinatorEntity[LunatoneCoordinator]):
    """Entity attached to the gateway itself."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LunatoneCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.uid}_{key}"
        self._attr_device_info = gateway_device_info(coordinator)


class LunatoneDeviceEntity(CoordinatorEntity[LunatoneCoordinator]):
    """Entity attached to one DALI control gear."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LunatoneCoordinator, device_id: int, key: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        dev = self.device
        # GTIN + identification number when known, so entities follow the
        # physical gear when a DALI scan assigns new short addresses
        ident = coordinator.device_key(dev)
        self._attr_unique_id = f"{coordinator.uid}_{ident}_{key}"
        types = dev.get("daliTypes") or []
        model = ", ".join(f"DT{t} {DALI_TYPES.get(t, '')}".strip() for t in types) or "DALI gear"
        identity = coordinator.identity(dev)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.uid}_{ident}")},
            manufacturer=identity.get("manufacturer") or "DALI",
            name=dev.get("name") or f"DALI {ident}",
            model=model,
            model_id=f"Line {dev.get('line', 0)} / A{dev.get('address')}",
            serial_number=str(identity["serial"]) if identity.get("serial") else None,
            sw_version=identity.get("firmware"),
            **via_gateway(coordinator),
        )

    @property
    def device(self) -> dict[str, Any]:
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data.devices.get(self.device_id, {})

    @property
    def features(self) -> dict[str, Any]:
        return self.device.get("features") or {}

    @property
    def available(self) -> bool:
        return super().available and self.device_id in (self.coordinator.data.devices if self.coordinator.data else {})


def feature_status(features: dict[str, Any], name: str, default: Any = None) -> Any:
    value = features.get(name)
    if isinstance(value, dict):
        return value.get("status", default)
    return default


def input_device_info(
    coordinator: LunatoneCoordinator, line: int, address: int | str, name: str | None = None
) -> DeviceInfo:
    """Device for a DALI control device (sensor / push button) on the bus."""
    found = coordinator.control_device(line, address) or {}
    return DeviceInfo(
        identifiers={(DOMAIN, f"{coordinator.uid}_input_{line}_{address}")},
        manufacturer=found.get("manufacturer") or "DALI",
        name=name or f"DALI input D{address} (line {line})",
        model="DALI-2 control device",
        model_id=f"Line {line} / D{address}",
        serial_number=str(found["serial"]) if found.get("serial") else None,
        sw_version=found.get("firmware"),
        **via_gateway(coordinator),
    )


class LunatoneGatewaySensorEntity(CoordinatorEntity[LunatoneCoordinator]):
    """Entity for a sensor reported by the gateway's /sensors endpoint."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LunatoneCoordinator, sensor_id: int) -> None:
        super().__init__(coordinator)
        self.sensor_id = sensor_id
        sensor = self.sensor
        self._attr_unique_id = f"{coordinator.uid}_sensor{sensor_id}"
        addr = sensor.get("daliSensorAddress")
        if sensor.get("addressType") == "dali" and isinstance(addr, dict):
            self._attr_device_info = input_device_info(
                coordinator, addr.get("line", 0), addr.get("address", 0)
            )
            self._attr_name = sensor.get("name") or None
        else:
            self._attr_device_info = gateway_device_info(coordinator)
            self._attr_name = sensor.get("name") or f"Sensor {sensor_id}"

    @property
    def sensor(self) -> dict[str, Any]:
        return self.coordinator.data.sensors.get(self.sensor_id, {}) if self.coordinator.data else {}

    @property
    def available(self) -> bool:
        return super().available and self.sensor_id in self.coordinator.data.sensors

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        s = self.sensor
        return {
            "sensor_type": s.get("type"),
            "address_type": s.get("addressType"),
            "dali_address": s.get("daliSensorAddress"),
            "timestamp": s.get("timestamp"),
        }
