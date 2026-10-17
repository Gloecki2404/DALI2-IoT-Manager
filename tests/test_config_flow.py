"""Config flow tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dali2_iot.api import LunatoneConnectionError
from custom_components.dali2_iot.const import DOMAIN

from .conftest import HOST, UID, load

PROBE = "custom_components.dali2_iot.config_flow.LunatoneApi.info"
SETUP = "custom_components.dali2_iot.async_setup_entry"


async def test_manual_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "manual"})
    assert result["step_id"] == "manual"

    with patch(PROBE, AsyncMock(side_effect=LunatoneConnectionError("nope"))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "10.0.0.1"})
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(PROBE, AsyncMock(return_value=load("info.json"))), patch(SETUP, AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": HOST})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": HOST}
    assert result["result"].unique_id == UID


async def test_hassio_discovery(hass: HomeAssistant) -> None:
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo

    info = HassioServiceInfo(
        config={"host": HOST}, name="DALI-2 IoT Manager", slug="dali2_iot_manager", uuid="1234"
    )
    with patch(PROBE, AsyncMock(return_value=load("info.json"))):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "hassio_confirm"
    with patch(SETUP, AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": HOST}
