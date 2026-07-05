"""Minimal STOMP-over-WebSocket client for CocktailPi's live push topics.

CocktailPi pushes real-time state (cocktail production progress, per-pump
running state, ...) over a STOMP connection at ``/websocket/`` rather than
exposing it via REST (see the "WebSocket" section of
``documentation/API.md``). There's no mainstream STOMP client that plays well
with Home Assistant's aiohttp session, so this hand-rolls just enough of the
STOMP 1.2 text framing to CONNECT, SUBSCRIBE, and receive MESSAGE frames.

Per the CocktailPi backend, all pushes are sent via
``SimpMessagingTemplate.convertAndSendToUser``, which Spring routes through a
per-user queue - clients must SUBSCRIBE to ``/user/<topic>`` (not the raw
``/topic/<...>``) to receive anything.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

_NULL = "\x00"
_RECONNECT_MIN_SECONDS = 2
_RECONNECT_MAX_SECONDS = 60


def _encode_frame(command: str, headers: dict[str, str], body: str = "") -> str:
    lines = [command, *(f"{key}:{value}" for key, value in headers.items()), "", body]
    return "\n".join(lines) + _NULL


def _decode_frame(raw: str) -> tuple[str, dict[str, str], str]:
    head, _, body = raw.partition("\n\n")
    lines = head.split("\n")
    command = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        key, _, value = line.partition(":")
        headers[key] = value
    return command, headers, body


def _parse_body(body: str) -> Any:
    """CocktailPi sends JSON payloads, but literal string sentinels like
    "DELETE" may or may not be JSON-quoted depending on Spring's message
    converter selection - handle both.
    """
    try:
        return json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return body


class CocktailPiWebSocketClient:
    """Keeps a STOMP-over-WebSocket connection to CocktailPi alive with auto-reconnect."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        token_provider: Callable[[], str | None],
    ) -> None:
        self._session = session
        host_and_port = base_url.split("://", 1)[-1]
        ws_scheme = "wss" if base_url.startswith("https") else "ws"
        self._ws_url = f"{ws_scheme}://{host_and_port}/websocket/"
        self._host = host_and_port.split(":")[0]
        self._token_provider = token_provider
        self._subscriptions: dict[str, tuple[str, Callable[[Any], None]]] = {}
        self._task: asyncio.Task | None = None
        self._stopping = False

    def subscribe(self, destination: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for a /user-prefixed destination.

        Must be called before async_start(); subscriptions are (re-)sent on
        every connect, including after a reconnect.
        """
        sub_id = f"sub-{len(self._subscriptions)}"
        self._subscriptions[sub_id] = (destination, callback)

    def async_start(self) -> None:
        """Start the background connect/listen/reconnect loop."""
        if self._task is not None:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._async_run_forever())

    async def async_stop(self) -> None:
        """Stop the client and close the connection."""
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def _async_run_forever(self) -> None:
        backoff = _RECONNECT_MIN_SECONDS
        while not self._stopping:
            try:
                await self._async_connect_and_listen()
                backoff = _RECONNECT_MIN_SECONDS
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("CocktailPi websocket disconnected: %s", err)
            if self._stopping:
                return
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _RECONNECT_MAX_SECONDS)

    async def _async_connect_and_listen(self) -> None:
        token = self._token_provider()
        async with self._session.ws_connect(self._ws_url, heartbeat=20) as ws:
            connect_headers = {
                "accept-version": "1.1,1.2",
                "host": self._host,
                # Disable STOMP-level heartbeats; aiohttp's heartbeat= param
                # above already keeps the underlying WS connection alive.
                "heart-beat": "0,0",
            }
            if token:
                connect_headers["Authorization"] = f"Bearer {token}"
            await ws.send_str(_encode_frame("CONNECT", connect_headers))

            buffer = ""
            connected = False
            async for msg in ws:
                if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue

                buffer += msg.data
                while _NULL in buffer:
                    raw, buffer = buffer.split(_NULL, 1)
                    if not raw.strip("\n"):
                        continue  # server heartbeat (bare newline)
                    command, headers, body = _decode_frame(raw)

                    if command == "CONNECTED":
                        connected = True
                        for sub_id, (destination, _cb) in self._subscriptions.items():
                            await ws.send_str(
                                _encode_frame(
                                    "SUBSCRIBE", {"id": sub_id, "destination": destination}
                                )
                            )
                    elif command == "MESSAGE":
                        sub_id = headers.get("subscription")
                        entry = self._subscriptions.get(sub_id) if sub_id else None
                        if entry is not None:
                            _destination, callback = entry
                            callback(_parse_body(body))
                    elif command == "ERROR":
                        _LOGGER.warning("CocktailPi websocket STOMP error: %s", body)

            if not connected:
                raise ConnectionError("Never received a STOMP CONNECTED frame")
