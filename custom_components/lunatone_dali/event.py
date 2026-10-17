"""Event entities – DALI-2 push buttons and sensors learned from bus events."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LunatoneConfigEntry
from .const import SIGNAL_INPUT_EVENT, SIGNAL_NEW_INPUT
from .coordinator import LunatoneCoordinator
from .dali_decode import BUTTON_EVENT_TYPES, OCCUPANCY_EVENT_TYPES, DaliEvent
from .entity import input_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunatoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(DaliInputEvent(coordinator, key) for key in list(coordinator.inputs))

    @callback
    def _new(key: str) -> None:
        async_add_entities([DaliInputEvent(coordinator, key)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_INPUT.format(coordinator.uid), _new)
    )


class DaliInputEvent(CoordinatorEntity[LunatoneCoordinator], EventEntity):
    """One instance (e.g. a single button) of a DALI-2 input device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LunatoneCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self.key = key
        meta = coordinator.inputs[key]
        self.kind = meta.get("kind", "unknown")
        line = meta.get("line", 0)
        addr = meta.get("short_address", 0)
        self._attr_unique_id = f"{coordinator.uid}_input_{key}"
        self._attr_device_info = input_device_info(coordinator, line, addr)
        inst = meta.get("instance_number")
        inst_label = f"#{inst}" if inst is not None else f"T{meta.get('instance_type')}"
        if self.kind == "push_button":
            self._attr_device_class = EventDeviceClass.BUTTON
            self._attr_event_types = BUTTON_EVENT_TYPES
            self._attr_translation_key = "push_button"
        elif self.kind == "occupancy_sensor":
            self._attr_event_types = OCCUPANCY_EVENT_TYPES
            self._attr_translation_key = "occupancy_event"
        elif self.kind == "light_sensor":
            self._attr_event_types = ["illuminance"]
            self._attr_translation_key = "light_event"
        else:
            self._attr_event_types = ["event", "position"]
            self._attr_translation_key = "generic_event"
        self._attr_translation_placeholders = {"instance": inst_label}

    @property
    def available(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_INPUT_EVENT.format(f"{self.coordinator.uid}_{self.key}"),
                self._handle_event,
            )
        )

    @callback
    def _handle_event(self, evt: DaliEvent) -> None:
        etype = evt.event_type or "event"
        attrs: dict[str, Any] = {"info": evt.info, **evt.attributes}
        if etype not in self.event_types:
            return
        self._trigger_event(etype, attrs)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Coordinator updates carry no information for event entities."""
