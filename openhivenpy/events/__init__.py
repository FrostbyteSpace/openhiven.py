"""
Module that stores the EventListeners Methods and Classes for listening to WebSocket Events
---
Under MIT License
Copyright © 2020 Frostbyte Development Team
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from .parsers import HivenParsers

import asyncio
import sys
import inspect
import logging
import typing
from functools import wraps

from ..exception import UnknownEventError, ExpectedAsyncFunction
from .. import utils

__all__ = ['SingleDispatchEventListener', 'HivenEventHandler']

logger = logging.getLogger(__name__)


def add_listener(client, listener):
    """
    Adds the listener to the client cache and will create a new list if the event_name does not exist yet!

    :param client: The HivenClient needed for adding the new listener
    :param listener: The Listener that will be added to the registered event_listeners
    """
    if client.active_listeners.get(listener.event_name):
        client.active_listeners[listener.event_name].append(listener)
    else:
        client.active_listeners[listener.event_name] = [listener]


def remove_listener(client, listener):
    """
    Removes the listener from the list and returns it

    :param client: The HivenClient needed for the popping
    :param listener: The Listener that will be removed
    """
    if client.active_listeners.get(listener.event_name):
        client.active_listeners[listener.event_name].remove(listener)
    else:
        raise KeyError("The listener does not exist with the event_name in the HivenClient")


class SingleDispatchEventListener:
    """ EventListener Class that will be called only once and will store the events data, args and kwargs """
    def __init__(self, client, event_name: str, coro: typing.Union[typing.Callable, typing.Coroutine, None]):
        self.coro = coro
        self.event_name = event_name
        self._client = client
        self._dispatched = False
        self._event_data = None
        self._args = None
        self._kwargs = None
        add_listener(client, self)

    def __str__(self):
        return f"<SingleDispatchEventListener for event {self.event_name}>"

    def __repr__(self):
        info = [
            ('event_name', getattr(self, 'event_name', None)),
            ('dispatched', self.dispatched),
            ('coro', getattr(self, 'coro', None))
        ]
        return '<SingleDispatchEventListener {}>'.format(' '.join('%s=%s' % t for t in info))

    def __call__(self, event_data: dict, *args, **kwargs):
        """
        Dispatches the EventListener and calls a coroutine if one was passed

        :param event_data: Data of the received event
        :param args: Args that will be passed to the coroutine
        :param kwargs: Kwargs that will be passed to the coroutine
        :return: Returns the passed event_data
        """
        return self.dispatch(event_data, *args, **kwargs)

    @property
    def dispatched(self) -> bool:
        return getattr(self, '_dispatched', False)

    @property
    def event_data(self):
        return getattr(self, '_event_data')

    @property
    def args(self) -> tuple:
        return getattr(self, '_args')

    @property
    def kwargs(self) -> dict:
        return getattr(self, '_kwargs')

    async def dispatch(self, event_data: dict, *args, **kwargs) -> dict:
        """
        Dispatches the EventListener and calls a coroutine if one was passed

        :param event_data: Data of the received event
        :param args: Args that will be passed to the coroutine
        :param kwargs: Kwargs that will be passed to the coroutine
        :return: Returns the passed event_data
        """
        self._event_data = event_data
        try:
            if inspect.iscoroutinefunction(self.coro):
                self._args = args
                self._kwargs = kwargs
                await self.coro(*args, **kwargs)
        except Exception as e:
            utils.log_traceback(
                msg=f"[EVENTS] EventListener for the event '{self.event_name}' failed to execute due to an exception:",
                suffix=f"{sys.exc_info()[0].__name__}: {e}!"
            )
        self._dispatched = True
        remove_listener(self._client, self)
        return event_data


class MultiDispatchEventListener:
    """ EventListener Class that is used primarily for EventListeners that will be called multiple times """
    def __init__(self, client, event_name: str, coro: typing.Union[typing.Callable, typing.Coroutine, None]):
        self.coro = coro
        self.event_name = event_name
        self._client = client
        add_listener(client, self)

    def __str__(self):
        return f"<MultiDispatchEventListener for event {self.event_name}>"

    def __repr__(self):
        info = [
            ('event_name', getattr(self, 'event_name', None)),
            ('coro', getattr(self, 'coro', None))
        ]
        return '<MultiDispatchEventListener {}>'.format(' '.join('%s=%s' % t for t in info))

    def __call__(self, event_data: dict, *args, **kwargs):
        """
        Dispatches the EventListener and calls a coroutine if one was passed

        :param event_data: Data of the received event
        :param args: Args that will be passed to the coroutine
        :param kwargs: Kwargs that will be passed to the coroutine
        :return: Returns the passed event_data
        """
        return self.dispatch(event_data, *args, **kwargs)

    async def dispatch(self, event_data, *args, **kwargs) -> dict:
        """
        Dispatches the EventListener and calls a coroutine if one was passed

        :param event_data: Data of the received event
        :param args: Args that will be passed to the coroutine
        :param kwargs: Kwargs that will be passed to the coroutine
        :return: Returns the passed event_data
        """
        try:
            if inspect.iscoroutinefunction(self.coro):
                await self.coro(*args, **kwargs)
        except Exception as e:
            utils.log_traceback(
                msg=f"[EVENTS] EventListener for the event '{self.event_name}' failed to execute due to an exception:",
                suffix=f"{sys.exc_info()[0].__name__}: {e}!"
            )
        return event_data


class HivenEventHandler:
    """
    Events class used to register the main event listeners.
    Is inherited by the HivenClient for easier access.
    """
    def __init__(self, hiven_parsers: HivenParsers):
        self.parsers = hiven_parsers
        self._active_listeners = {}
        # List of available callable events that have parsers defined
        self._events = [
            'connection_start', 'init', 'ready', 'user_update',
            'house_join', 'house_remove', 'house_update', 'house_delete', 'house_delete', 'house_downtime',
            'room_create', 'room_update', 'room_delete',
            'house_member_join', 'house_member_leave', 'house_member_enter', 'house_member_exit', 'member_update',
            'house_member_chunk', 'batch_house_member_update',
            'house_entity_update'
            'relationship_update',
            'presence_update',
            'message_create', 'message_update', 'message_delete',
            'typing_start'
        ]

        # Searching through the HivenClient to find all async functions that were registered for event_listening
        # Regular functions will NOT be registered and only if they are async! This will avoid that errors are thrown
        # when trying to call the functions using 'await'
        for listener in inspect.getmembers(self, predicate=inspect.iscoroutinefunction):
            # listener[0] => name
            func_name = listener[0].replace('on_', '')
            coro = listener[1]
            if func_name in self._events:
                self.add_new_multi_event_listener(func_name, coro)
                logger.debug(f"[EVENTS] Event {listener[0]} registered")

    @property
    def active_listeners(self) -> dict:
        return getattr(self, '_active_listeners', {})

    async def dispatch(self, event_name: str, event_data: dict = {}, *args, **kwargs):
        """
        Dispatches all active EventListeners for the specified event.

        ---

        Will run all tasks before returning! Will be used in the

        :param event_name: The name of the event that should be triggered
        :param event_data: The data of the received event
        :param args: Args that will be passed to the coroutines
        :param kwargs: Kwargs that will be passed to the coroutines
        """
        events = self.active_listeners.get(event_name.replace('on_', ''))
        if events:
            tasks = [e(event_data, *args, **kwargs) for e in events]
            await asyncio.gather(*tasks)

    async def wait_for(self,
                       event_name: str,
                       coro: typing.Union[typing.Callable, typing.Coroutine, None] = None) -> (list, dict):
        """
        Waits for an event to be triggered and then returns the *args and **kwargs passed

        :param event_name: Name of the event to wait for
        :param coro: Coroutine that can be passed to be additionally triggered when received
        :return: A tuple of the args and kwargs => [0] = args and [1] = kwargs
        """
        event_name = event_name.replace('on_', '')
        listener = self.add_new_single_event_listener(event_name, coro)
        while not listener.dispatched:
            await asyncio.sleep(.05)

        return listener.args, listener.kwargs

    def event(self, coro: typing.Union[typing.Callable, typing.Coroutine] = None):
        """
        Decorator used for registering Client Events

        :param coro: Function that should be wrapped and registered
        """
        def decorator(coro: typing.Union[typing.Callable, typing.Coroutine]):
            if not inspect.iscoroutinefunction(coro):
                raise ExpectedAsyncFunction("The decorated event_listener requires to be async!")

            if coro.__name__.replace('on_', '') not in self._events:
                raise UnknownEventError("The passed event_listener was not found in the available events!")

            @wraps(coro)
            async def wrapper(*args, **kwargs):
                return await coro(*args, **kwargs)

            func_name = coro.__name__.replace('on_', '')
            self.add_new_multi_event_listener(func_name, coro)
            logger.debug(f"[EVENTS] Event {func_name} registered")

            return coro  # func can still be used normally outside the event listening process

        if coro is None:
            return decorator
        else:
            return decorator(coro)

    def add_new_multi_event_listener(self,
                                     event_name: str,
                                     coro: typing.Union[typing.Callable,
                                                        typing.Coroutine]) -> MultiDispatchEventListener:
        """
        Adds a new event listener to the list of active listeners

        :param event_name: The key/name of the event the EventListener should be listening to
        :param coro: Coroutine that should be called when the EventListener was dispatched
        :returns: The newly created EventListener
        """
        event_name = event_name.replace('on_', '')
        if self.active_listeners.get(event_name) is None:
            self.active_listeners[event_name] = []

        listener = MultiDispatchEventListener(self, event_name, coro)
        return listener

    def add_new_single_event_listener(self,
                                      event_name: str,
                                      coro: typing.Union[typing.Callable,
                                                         typing.Coroutine]) -> SingleDispatchEventListener:
        """
        Adds a new single dispatch event listener to the list of active listeners

        :param event_name: The key/name of the event the EventListener should be listening to
        :param coro: Coroutine that should be called when the EventListener was dispatched
        :returns: The newly created EventListener
        """
        event_name = event_name.replace('on_', '')
        if self.active_listeners.get(event_name) is None:
            self.active_listeners[event_name] = []

        listener = SingleDispatchEventListener(self, event_name, coro)
        return listener
