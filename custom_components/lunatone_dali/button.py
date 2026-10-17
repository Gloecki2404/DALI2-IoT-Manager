"""Buttons – gateway maintenance actions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LunatoneConfigEntry
from .api import LunatoneError
from .coordinator import LunatoneCoordinator
from .entity import LunatoneEntity


@dataclass(frozen=True, kw_only=True)
class ActionDescription(ButtonEntityDescription):
    action: Callable[[LunatoneCoordinator], Awaitable[object]]


async def _refresh(coord: LunatoneCoordinator) -> None:
    await coord.async_refresh_extras()
    await coord.async_request_refresh()


BUTTONS: tuple[ActionDescription, ...] = (
    ActionDescription(
        key="reboot",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        action=lambda c: c.api.reboot(),
    ),
    ActionDescription(
        key="refresh",
        translation_key="refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        action=_refresh,
    ),
    ActionDescription(
        key="refresh_sensors",
        translation_key="refresh_sensors",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        action=lambda c: c.api.refresh_sensors(),
    ),
    ActionDescription(
        key="scan",
        translation_key="scan",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        action=lambda c: c.api.start_scan(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LunatoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(GatewayButton(coordinator, desc) for desc in BUTTONS)


class GatewayButton(LunatoneEntity, ButtonEntity):
    entity_description: ActionDescription

    def __init__(self, coordinator: LunatoneCoordinator, desc: ActionDescription) -> None:
        super().__init__(coordinator, f"button_{desc.key}")
        self.entity_description = desc

    async def async_press(self) -> None:
        try:
            await self.entity_description.action(self.coordinator)
        except LunatoneError as err:
            raise HomeAssistantError(str(err)) from err
