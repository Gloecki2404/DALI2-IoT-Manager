"""Switches – gateway settings and gateway automations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunatoneConfigEntry
from .api import LunatoneError
from .coordinator import LunatoneCoordinator
from .entity import LunatoneEntity

SETTINGS = {
    "dali_ping": "dali_ping",
    "log_file_enabled": "log_file",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunatoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SettingSwitch(coordinator, key, tkey)
        for key, tkey in SETTINGS.items()
        if key in coordinator.data.settings
    )
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for kind, items in coordinator.data.automations.items():
            for item in items:
                key = f"{kind}{item.get('id')}"
                if item.get("id") is None or key in known:
                    continue
                known.add(key)
                new.append(AutomationSwitch(coordinator, kind, item["id"]))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class SettingSwitch(LunatoneEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LunatoneCoordinator, key: str, tkey: str) -> None:
        super().__init__(coordinator, f"setting_{key}")
        self._key = key
        self._attr_translation_key = tkey
        if key == "log_file_enabled":
            self._attr_entity_registry_enabled_default = False

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.settings.get(self._key)

    async def _set(self, value: bool) -> None:
        try:
            result = await self.coordinator.api.set_settings({self._key: value})
        except LunatoneError as err:
            raise HomeAssistantError(str(err)) from err
        if isinstance(result, dict):
            self.coordinator.data.settings.update(result)
        else:
            self.coordinator.data.settings[self._key] = value
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class AutomationSwitch(LunatoneEntity, SwitchEntity):
    """Enable/disable (or for sequences: run/stop) a gateway automation."""

    def __init__(self, coordinator: LunatoneCoordinator, kind: str, item_id: int) -> None:
        super().__init__(coordinator, f"automation_{kind}_{item_id}")
        self.kind = kind
        self.item_id = item_id
        self._attr_translation_key = f"automation_{kind}"
        self._attr_translation_placeholders = {"name": self._item.get("name") or f"#{item_id}"}

    @property
    def _item(self) -> dict[str, Any]:
        for item in self.coordinator.data.automations.get(self.kind, []):
            if item.get("id") == self.item_id:
                return item
        return {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._item)

    @property
    def is_on(self) -> bool | None:
        item = self._item
        if self.kind == "sequence":
            return item.get("active")
        return item.get("enabled")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._item
        attrs = {"automation_id": self.item_id, "kind": self.kind, "enabled": item.get("enabled")}
        if self.kind == "sequence":
            attrs.update(loop=item.get("loop"), repeat=item.get("repeat"), steps=len(item.get("steps") or []))
        if self.kind == "scheduler":
            attrs.update(recall_mode=item.get("recallMode"), recall_time=item.get("recallTime"))
        return attrs

    async def _set(self, on: bool) -> None:
        api = self.coordinator.api
        try:
            if self.kind == "sequence":
                if on:
                    await api.automation_start(self.kind, self.item_id)
                else:
                    await api.automation_stop(self.kind, self.item_id)
            else:
                await api.automation_update(self.kind, self.item_id, {"enabled": on})
        except LunatoneError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
