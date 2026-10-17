"""Async client for the Lunatone DALI-2 IoT REST and websocket API."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class LunatoneError(Exception):
    """Generic API error."""


class LunatoneConnectionError(LunatoneError):
    """Gateway not reachable."""


class LunatoneNotSupported(LunatoneError):
    """The requested feature is not supported by the device (HTTP 501)."""


class LunatoneApi:
    """Thin wrapper around the gateway's HTTP API."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = host.strip().rstrip("/")
        if self.host.startswith(("http://", "https://")):
            self.base_url = self.host
        else:
            self.base_url = f"http://{self.host}"
        self.ws_url = self.base_url.replace("http", "ws", 1) + "/"

    # ------------------------------------------------------------------ core
    async def request(
        self,
        method: str,
        path: str,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a request and return decoded JSON (or None)."""
        url = f"{self.base_url}{path}"
        try:
            async with self._session.request(
                method, url, json=json_data, params=params, timeout=REQUEST_TIMEOUT
            ) as resp:
                text = await resp.text()
                if resp.status == 501:
                    raise LunatoneNotSupported(_detail(text) or "not supported")
                if resp.status >= 400:
                    raise LunatoneError(
                        f"{method} {path} failed ({resp.status}): {_detail(text) or text[:200]}"
                    )
                if not text:
                    return None
                try:
                    return json.loads(text)
                except ValueError:
                    return text
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            reason = str(err) or ("timeout" if isinstance(err, asyncio.TimeoutError) else type(err).__name__)
            raise LunatoneConnectionError(f"{method} {path}: {reason}") from err

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, data: Any = None, **kw: Any) -> Any:
        return await self.request("POST", path, json_data=data, **kw)

    async def put(self, path: str, data: Any = None, **kw: Any) -> Any:
        return await self.request("PUT", path, json_data=data, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        return await self.request("DELETE", path, **kw)

    # ------------------------------------------------------------- endpoints
    async def info(self) -> dict[str, Any]:
        return await self.get("/info")

    async def devices(self) -> list[dict[str, Any]]:
        return (await self.get("/devices") or {}).get("devices", [])

    async def device(self, device_id: int) -> dict[str, Any]:
        return await self.get(f"/device/{device_id}")

    async def update_device(self, device_id: int, data: dict[str, Any]) -> dict[str, Any]:
        return await self.put(f"/device/{device_id}", data)

    async def zones(self) -> list[dict[str, Any]]:
        return (await self.get("/zones") or {}).get("zones", [])

    async def sensors(self) -> list[dict[str, Any]]:
        return (await self.get("/sensors") or {}).get("sensors", [])

    async def refresh_sensors(self) -> list[dict[str, Any]]:
        return (await self.post("/sensors") or {}).get("sensors", [])

    async def settings(self) -> dict[str, Any]:
        return await self.get("/settings")

    async def set_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self.put("/settings", data)

    async def scan(self) -> dict[str, Any]:
        return await self.get("/dali/scan")

    async def start_scan(
        self,
        new_installation: bool = False,
        no_addressing: bool = False,
        lines: list[int] | None = None,
    ) -> dict[str, Any]:
        return await self.post(
            "/dali/scan",
            {
                "newInstallation": new_installation,
                "noAddressing": no_addressing,
                "useLines": lines or [],
            },
        )

    async def cancel_scan(self) -> Any:
        return await self.post("/dali/scan/cancel")

    async def line_status(self, line: int) -> dict[str, Any]:
        return await self.get(f"/dali/readStatus/{line}")

    async def energy(self, device_id: int) -> dict[str, Any]:
        return await self.get(f"/device/{device_id}/energyReporting")

    async def diagnostics(self, device_id: int) -> dict[str, Any]:
        return await self.get(f"/device/{device_id}/diagnosticsMaintenance")

    async def scenes(self, device_id: int, refresh: bool = False) -> dict[str, Any]:
        if refresh:
            return await self.post(f"/device/{device_id}/scenes")
        return await self.get(f"/device/{device_id}/scenes")

    async def control(self, target: str, target_id: int | None, data: dict[str, Any]) -> None:
        """Send a control command. target: device | group | zone | broadcast."""
        if target == "broadcast":
            await self.post("/broadcast/control", data)
        else:
            await self.post(f"/{target}/{target_id}/control", data)

    async def send_dali16(self, line: int, frames: list[dict[str, int]]) -> list[int]:
        return await self.post(f"/dali/sendDali16/{line}", frames) or []

    async def send_dali24(self, line: int, frames: list[dict[str, int]]) -> list[int]:
        return await self.post(f"/dali/sendDali24/{line}", frames) or []

    async def reboot(self) -> None:
        await self.post("/reboot")

    async def automations(self) -> dict[str, list[dict[str, Any]]]:
        """Return all gateway automations grouped by kind."""
        result: dict[str, list[dict[str, Any]]] = {}
        for kind, path, key in (
            ("sequence", "/automations/sequences", "sequences"),
            ("scheduler", "/automations/schedules", "schedulers"),
            ("circadian", "/automations/circadians", "circadians"),
            ("triggerAction", "/automations/triggerActions", "triggerActions"),
        ):
            try:
                data = await self.get(path)
            except LunatoneNotSupported:
                data = None
            if isinstance(data, dict):
                result[kind] = data.get(key, [])
            elif isinstance(data, list):
                result[kind] = data
            else:
                result[kind] = []
        return result

    async def automation_get(self, kind: str, item_id: int) -> dict[str, Any]:
        return await self.get(f"/automations/{kind}/{item_id}")

    async def automation_update(self, kind: str, item_id: int, data: dict[str, Any]) -> Any:
        return await self.put(f"/automations/{kind}/{item_id}", data)

    async def automation_start(self, kind: str, item_id: int) -> Any:
        return await self.post(f"/automations/{kind}/{item_id}/start")

    async def automation_stop(self, kind: str, item_id: int) -> Any:
        return await self.post(f"/automations/{kind}/{item_id}/stop")

    # ------------------------------------------------------------- websocket
    async def listen(
        self,
        on_message: Callable[[dict[str, Any]], None],
        on_state: Callable[[bool], Awaitable[None] | None],
        stop: asyncio.Event,
    ) -> None:
        """Listen to the websocket forever, reconnecting with backoff."""
        backoff = 1.0
        while not stop.is_set():
            try:
                async with self._session.ws_connect(
                    self.ws_url, heartbeat=30, timeout=aiohttp.ClientWSTimeout(ws_close=10)
                ) as ws:
                    _LOGGER.debug("Websocket connected to %s", self.ws_url)
                    backoff = 1.0
                    res = on_state(True)
                    if asyncio.iscoroutine(res):
                        await res
                    async for msg in ws:
                        if stop.is_set():
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except ValueError:
                                continue
                            if isinstance(data, dict):
                                try:
                                    on_message(data)
                                except Exception:  # noqa: BLE001
                                    _LOGGER.exception("Error handling websocket message")
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Websocket error (%s), reconnecting in %.0fs", err, backoff)
            res = on_state(False)
            if asyncio.iscoroutine(res):
                await res
            if stop.is_set():
                break
            try:
                await asyncio.wait_for(stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 60)


def _detail(text: str) -> str | None:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, dict) and "detail" in data:
        detail = data["detail"]
        return detail if isinstance(detail, str) else json.dumps(detail)
    return None


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge a partial websocket update into cached data."""
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base
