"""Sensors – gateway sensors, energy reporting, diagnostics, gateway state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

try:  # HA >= 2026.x
    from homeassistant.const import UnitOfRatio

    PPM, PPB = UnitOfRatio.PARTS_PER_MILLION, UnitOfRatio.PARTS_PER_BILLION
except ImportError:  # pragma: no cover
    PPM, PPB = "ppm", "ppb"

from . import LunatoneConfigEntry
from .coordinator import LunatoneCoordinator, LunatoneData
from .entity import LunatoneDeviceEntity, LunatoneEntity, LunatoneGatewaySensorEntity

LINE_STATES = ["ok", "lowPower", "noPower", "notReachable"]
SCAN_STATES = ["not started", "cancelled", "done", "addressing", "in progress", "bus error"]

GATEWAY_SENSOR_TYPES: dict[str, tuple[SensorDeviceClass | None, str | None]] = {
    "temperature": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "airHumidity": (SensorDeviceClass.HUMIDITY, PERCENTAGE),
    "airPressure": (SensorDeviceClass.ATMOSPHERIC_PRESSURE, UnitOfPressure.HPA),
    "eCO2": (SensorDeviceClass.CO2, PPM),
    "VOC": (SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, PPB),
    "airQuality": (SensorDeviceClass.AQI, None),
    "light": (SensorDeviceClass.ILLUMINANCE, LIGHT_LUX),
}


@dataclass(frozen=True, kw_only=True)
class ValueDescription(SensorEntityDescription):
    """Description for a value in the energy/diagnostics dicts."""

    source: str  # "energy" | "diagnostics"
    convert: Callable[[Any], Any] | None = None


def _hours(value: Any) -> Any:
    return round(value / 3600, 1) if isinstance(value, (int, float)) else value


ENERGY_SENSORS: tuple[ValueDescription, ...] = (
    ValueDescription(
        key="activeEnergyWattHours", translation_key="active_energy", source="energy",
        device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING, suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    ValueDescription(
        key="activePowerWatt", translation_key="active_power", source="energy",
        device_class=SensorDeviceClass.POWER, native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ValueDescription(
        key="apparentEnergyVoltAmpereHours", translation_key="apparent_energy", source="energy",
        native_unit_of_measurement="VAh", state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="apparentPowerVoltAmpere", translation_key="apparent_power", source="energy",
        device_class=SensorDeviceClass.APPARENT_POWER, native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="activeEnergyLoadsideWattHours", translation_key="loadside_energy", source="energy",
        device_class=SensorDeviceClass.ENERGY, native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING, entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="activePowerLoadsideWatt", translation_key="loadside_power", source="energy",
        device_class=SensorDeviceClass.POWER, native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False,
    ),
)

_DIAG = EntityCategory.DIAGNOSTIC
DIAG_SENSORS: tuple[ValueDescription, ...] = (
    ValueDescription(
        key="controlGearOperatingTimeSeconds", translation_key="gear_operating_time", source="diagnostics",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING, entity_category=_DIAG, convert=_hours,
    ),
    ValueDescription(
        key="controlGearStartCounter", translation_key="gear_start_counter", source="diagnostics",
        state_class=SensorStateClass.TOTAL_INCREASING, entity_category=_DIAG,
    ),
    ValueDescription(
        key="controlGearExternalSupplyVoltageVoltRms", translation_key="supply_voltage", source="diagnostics",
        device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG,
    ),
    ValueDescription(
        key="controlGearExternalSupplyVoltageFrequencyHertz", translation_key="supply_frequency", source="diagnostics",
        device_class=SensorDeviceClass.FREQUENCY, native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG, entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="controlGearPowerFactor", translation_key="power_factor", source="diagnostics",
        device_class=SensorDeviceClass.POWER_FACTOR, state_class=SensorStateClass.MEASUREMENT,
        entity_category=_DIAG,
    ),
    ValueDescription(
        key="controlGearTemperatureCelsius", translation_key="gear_temperature", source="diagnostics",
        device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG,
    ),
    ValueDescription(
        key="controlGearOutputCurrentPercent", translation_key="output_current", source="diagnostics",
        native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG,
    ),
    ValueDescription(
        key="lightSourceStartCounter", translation_key="light_start_counter", source="diagnostics",
        state_class=SensorStateClass.TOTAL_INCREASING, entity_category=_DIAG,
    ),
    ValueDescription(
        key="lightSourceStartCounterResettable", translation_key="light_start_counter_resettable",
        source="diagnostics", state_class=SensorStateClass.TOTAL, entity_category=_DIAG,
        entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="lightSourceOnTimeSeconds", translation_key="light_on_time", source="diagnostics",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING, entity_category=_DIAG, convert=_hours,
    ),
    ValueDescription(
        key="lightSourceOnTimeResettableSeconds", translation_key="light_on_time_resettable",
        source="diagnostics", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL, entity_category=_DIAG, convert=_hours,
        entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="lightSourceVoltageVolt", translation_key="light_voltage", source="diagnostics",
        device_class=SensorDeviceClass.VOLTAGE, native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG,
    ),
    ValueDescription(
        key="lightSourceCurrentAmpere", translation_key="light_current", source="diagnostics",
        device_class=SensorDeviceClass.CURRENT, native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG,
    ),
    ValueDescription(
        key="lightSourceTemperatureCelsius", translation_key="light_temperature", source="diagnostics",
        device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT, entity_category=_DIAG,
    ),
    ValueDescription(
        key="ratedMedianUsefulLifeOfLuminaireHours", translation_key="rated_life", source="diagnostics",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=_DIAG, entity_registry_enabled_default=False,
    ),
    ValueDescription(
        key="ratedMedianUsefulLightSourceStarts", translation_key="rated_starts", source="diagnostics",
        entity_category=_DIAG, entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunatoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    base: list[SensorEntity] = [
        ScanStatusSensor(coordinator),
        ScanProgressSensor(coordinator),
        CountSensor(coordinator, "devices_total", lambda d: len(d.devices)),
        CountSensor(
            coordinator,
            "devices_unavailable",
            lambda d: sum(1 for x in d.devices.values() if not x.get("available", True)),
        ),
        CountSensor(
            coordinator,
            "devices_failure",
            lambda d: sum(
                1
                for x in d.devices.values()
                if (x.get("status") or {}).get("lampFailure")
                or (x.get("status") or {}).get("controlGearFailure")
            ),
        ),
        CountSensor(
            coordinator,
            "lights_on",
            lambda d: sum(
                1
                for x in d.devices.values()
                if ((x.get("features") or {}).get("switchable") or {}).get("status")
            ),
        ),
    ]
    base += [LineStatusSensor(coordinator, line) for line in coordinator.data.lines]
    async_add_entities(base)

    @callback
    def _add_new() -> None:
        new: list[SensorEntity] = []
        data = coordinator.data
        for sid, sensor in data.sensors.items():
            key = f"sensor{sid}"
            if key not in known and sensor.get("type") != "occupancy":
                known.add(key)
                new.append(GatewaySensor(coordinator, sid))
        for source, descs in (("energy", ENERGY_SENSORS), ("diagnostics", DIAG_SENSORS)):
            for dev_id, values in getattr(data, source).items():
                for desc in descs:
                    key = f"{source}{dev_id}_{desc.key}"
                    if key not in known and values.get(desc.key) is not None:
                        known.add(key)
                        new.append(DeviceValueSensor(coordinator, dev_id, desc))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class GatewaySensor(LunatoneGatewaySensorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: LunatoneCoordinator, sensor_id: int) -> None:
        super().__init__(coordinator, sensor_id)
        stype = self.sensor.get("type", "unknown")
        dclass, unit = GATEWAY_SENSOR_TYPES.get(stype, (None, None))
        self._attr_device_class = dclass
        self._attr_native_unit_of_measurement = self.sensor.get("unit") or unit
        if dclass == SensorDeviceClass.ATMOSPHERIC_PRESSURE and self._attr_native_unit_of_measurement not in (
            UnitOfPressure.HPA, UnitOfPressure.PA, UnitOfPressure.MBAR, UnitOfPressure.KPA
        ):
            self._attr_native_unit_of_measurement = unit
        if dclass == SensorDeviceClass.TEMPERATURE and self._attr_native_unit_of_measurement in ("C", "°C", "degC"):
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> Any:
        return self.sensor.get("value")


class DeviceValueSensor(LunatoneDeviceEntity, SensorEntity):
    entity_description: ValueDescription

    def __init__(self, coordinator: LunatoneCoordinator, device_id: int, desc: ValueDescription) -> None:
        super().__init__(coordinator, device_id, f"{desc.source}_{desc.key}")
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        values = getattr(self.coordinator.data, self.entity_description.source).get(self.device_id, {})
        value = values.get(self.entity_description.key)
        if self.entity_description.convert:
            return self.entity_description.convert(value)
        return value


class LineStatusSensor(LunatoneEntity, SensorEntity):
    _attr_translation_key = "line_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = LINE_STATES
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator, line: int) -> None:
        super().__init__(coordinator, f"line{line}_status")
        self.line = line
        self._attr_translation_placeholders = {"line": str(line)}

    @property
    def native_value(self) -> str | None:
        line = self.coordinator.data.lines.get(self.line)
        return line.get("lineStatus") if line else None


class ScanStatusSensor(LunatoneEntity, SensorEntity):
    _attr_translation_key = "scan_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [s.replace(" ", "_") for s in SCAN_STATES]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LunatoneCoordinator) -> None:
        super().__init__(coordinator, "scan_status")

    @property
    def native_value(self) -> str | None:
        status = self.coordinator.data.scan.get("status")
        return status.replace(" ", "_") if status else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        scan = self.coordinator.data.scan
        return {"found": scan.get("found"), "found_sensors": scan.get("foundSensors"), "lines": scan.get("lines")}


class ScanProgressSensor(LunatoneEntity, SensorEntity):
    _attr_translation_key = "scan_progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: LunatoneCoordinator) -> None:
        super().__init__(coordinator, "scan_progress")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.scan.get("progress")


class CountSensor(LunatoneEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: LunatoneCoordinator, key: str, func: Callable[[LunatoneData], int]
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._func = func
        if key != "lights_on":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int:
        return self._func(self.coordinator.data)
