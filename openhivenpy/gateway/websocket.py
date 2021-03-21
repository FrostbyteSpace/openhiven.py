import asyncio
import json
import logging
import os
import typing
import time
import aiohttp
from enum import IntEnum
from yarl import URL

from ..exceptions import RestartSessionError, SessionCreateError, WebSocketClosedError
from .messagebroker import MessageBroker

__all__ = ['HivenWebSocket']

logger = logging.getLogger(__name__)


class KeepAlive:
    def __init__(self, ws):
        self.ws = ws
        self._heartbeat = ws.heartbeat
        self._task = None
        self._active = False

    async def run(self):
        """ Runs the current KeepAlive process in a loop that can be cancelled using `KeepAlive.stop()` """
        self._active = True
        while self.ws.open and self._active:
            try:
                self._task = asyncio.create_task(asyncio.wait_for(self.ws.send_heartbeat(), 30))
                await asyncio.sleep(self._heartbeat / 1000)
            except asyncio.CancelledError:
                return
            except Exception:
                raise

    async def stop(self):
        """ Stops the running KeepAlive loop """
        if self._task:
            if self._task.cancelled():
                self._task.cancel()
        self._active = False
        self._task = None


class HivenWebSocket:
    def __init__(self, socket, *, loop: asyncio.AbstractEventLoop, log_ws_output: bool = False):
        self.socket = socket
        self.loop = loop
        self.parsers = None
        self.client = None
        self.endpoint = None
        self.keep_alive = None
        self.message_broker = None
        self.log_ws_output = log_ws_output
        self._open = False
        self._ready = False
        self._startup_time = None
        self._connection_start = None
        self._connection_status = "CLOSED"
        self._token = None
        self._heartbeat = None
        self._close_timeout = None

        # Close code used to represent the status of the aiohttp websocket after it closed
        self._close_code = None

    @classmethod
    async def create_from_client(cls,
                                 client,
                                 endpoint: URL,
                                 close_timeout: int,
                                 heartbeat: int,
                                 loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
                                 **kwargs):
        """ Creates a new WebSocket Instance and starts the Connection to Hiven """
        socket = await client.http.session.ws_connect(
            endpoint.human_repr(), timeout=close_timeout, heartbeat=heartbeat, max_msg_size=0
        )
        ws = cls(socket, loop=loop, **kwargs)
        ws.endpoint = endpoint
        ws.client = client
        ws.parsers = client.parsers
        ws._token = client.token
        ws._heartbeat = heartbeat
        ws._close_timeout = close_timeout

        ws.message_broker = MessageBroker(client)
        ws.keep_alive = KeepAlive(ws)

        return ws

    class OPCode(IntEnum):
        EVENT = 0
        CONNECTION_START = 1
        AUTH = 2
        HEARTBEAT = 3

    @property
    def token(self) -> str:
        return getattr(self, '_token', None)

    @property
    def startup_time(self) -> int:
        return getattr(self, '_startup_time', None)

    @property
    def connection_start(self) -> int:
        return getattr(self, '_connection_start', None)

    @property
    def open(self) -> bool:
        return getattr(self, '_open', None)

    @property
    def ready(self) -> bool:
        return getattr(self, '_ready', None)

    @property
    def heartbeat(self) -> int:
        return getattr(self, '_heartbeat', None)

    @property
    def close_timeout(self) -> int:
        return getattr(self, '_close_timeout', None)

    async def listening_loop(self):
        """ Listens infinitely for WebSocket Messages and will trigger events accordingly """
        while True:
            await self.wait_for_event()

    async def wait_for_event(self, handler: typing.Callable = None):
        """
        Waits for an event or websocket message and then triggers appropriately the events or raises Exceptions

        :param handler: Handler Awaitable that will be executed instead of `received_message()` if not None
        """
        msg = await self.socket.receive()

        logger.debug(f"[WEBSOCKET] Received WebSocket Message Type '{msg.type.name}'")

        if msg.type == aiohttp.WSMsgType.TEXT:
            return await self.received_message(msg) if handler is None else await handler(msg)

        elif msg.type == aiohttp.WSMsgType.BINARY:
            if type(msg) is bytes:
                msg = msg.data.decode("utf-8")
            else:
                return
            return await self.received_message(msg) if handler is None else await handler(msg)

        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING):
            logger.error("[WEBSOCKET] Received close frame from the Server! WebSocket will force restart!")
            raise RestartSessionError()

        elif msg.type == aiohttp.WSMsgType.CLOSED:
            self._open = False
            logger.info("[WEBSOCKET] Closing the WebSocket Connection and stopping the processes!")
            raise WebSocketClosedError()

        elif msg.type == aiohttp.WSMsgType.ERROR:
            logger.error(
                f"[WEBSOCKET] Encountered an Exception in the Websocket! {msg.extra}"
            )
            raise WebSocketClosedError(
                "[WEBSOCKET] Encountered an Exception in the Websocket!"
            )

    async def received_message(self, msg):
        """
        Awaits a new incoming message and handles it.
        Will raise an exception if a close frame was received
        """
        msg = msg.json()
        op, event, data = self.extract_event(msg)

        if op == self.OPCode.CONNECTION_START:
            self._connection_start = time.time()
            self._open = True

        elif op == self.OPCode.EVENT:
            logger.debug(f"[WEBSOCKET] Received Websocket Event: {event}")

            if event == 'INIT_STATE':
                await self.received_init(msg)
            else:
                await self.parsers.dispatch(event, data)
            return

        else:
            logger.warning(f"[WEBSOCKET] Received unknown websocket op-code message: {op}: {msg}")

    async def received_init(self, msg: dict):
        """
        Receives the init message from the host and updates the client cache.
        Will shield the normal message handler from receiving events until the initialisation succeeded.

        :returns: A List of all other events that were received during initialisation that will now need to be called
        """
        await self.client.call_listeners('init')

        data = msg['d']
        house_memberships = data.get('house_memberships', {})
        self.client.storage.update_all(data)

        additional_events = []
        while len(house_memberships) != len(self.client.storage['houses']):
            ws_event = await self.wait_for_event(handler=self.received_init_event)
            if msg:
                op, event, d = self.extract_event(ws_event.json())
                if event == "HOUSE_JOIN":
                    self.client.storage.add_or_update_house(d)
                else:
                    additional_events.append(ws_event)

        # Executing all additional events that were received during the initialisation and were ignored
        for event in additional_events:
            await self.received_message(event)

        self._startup_time = time.time() - self._connection_start
        logger.debug("[WEBSOCKET] Received Init Frame from the Hiven Swarm and initialised the Client Cache!")
        logger.info(f"[CLIENT] Ready after {self.startup_time}s")

        # Delaying the receiving process until all ready-state listeners were called
        await self.client.call_listeners('ready')
        self._ready = True

    async def received_init_event(self, msg):
        """ Only intended for the purpose of initialising the Client! Will be called by `received_init` on startup """
        _msg = msg.json()
        op = _msg.get('op')

        if op == self.OPCode.EVENT:
            return msg
        else:
            logger.warning(f"[WEBSOCKET] Received unknown websocket op-code message: {op}: {msg}")
            return msg

    async def send_heartbeat(self):
        """ Sends a heartbeat with the additional op-code for keeping the connection alive"""
        try:
            await self.socket.send_str(str(json.dumps({
                "op": self.OPCode.HEARTBEAT
            })))
        except Exception as e:
            raise RestartSessionError("Failed to send heartbeat to WebSocket host!")

    async def send_auth(self):
        """ Sends the authentication header to the Hiven Endpoint"""
        try:
            auth = str(json.dumps({
                "op": self.OPCode.AUTH,
                "d": {
                    "token": self.token
                }
            }))
            await self.socket.send_str(auth)
        except Exception as e:
            raise SessionCreateError(f"Failed to send auth to the host due to exception: {e}")

    def extract_event(self, msg: dict) -> typing.Tuple[int, str, dict]:
        """
        Formats the incoming msg and returns it in tuple form

        :param msg: The raw WebSocket Message
        :return: The op-code, event-name and data in tuple form
        """
        return msg.get('op'), msg.get('e'), msg.get('d')
