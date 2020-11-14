import asyncio 
import logging
from functools import wraps

from openhivenpy.Utils import dispatch_func_if_exists

logger = logging.getLogger(__name__) 
    
class EventHandler():
    """`openhivenpy.Events.EventHandler` 
    
    Openhivenpy Event Handler
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    
    Event Handler for the HivenClient Class. Functions will be called from the
    websocket class and if the user registered an event response with the
    decorator @HivenClient.event, it will be called and executed.
    
    """
    def __init__(self, call_obj: object):
        self.call_obj = call_obj
        if call_obj == None: 
            logger.debug("Passed object where the events should be called from is None!")

    def event(self):
        """`openhivenpy.Events.Events.event`
        
        Event Decorator
        ---------------
        
        Decorator used for registering HivenClient Events
        
        """
        def decorator(func):
            @wraps(func) 
            async def wrapper(*args, **kwargs): 
                return await func(*args, **kwargs)
            
            setattr(self, func.__name__, wrapper) # Adding the function to the object

            logger.debug(f"Event {func.__name__} registered")

            return func # returning func means func can still be used normally

        return decorator

    async def connection_start(self) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_connection_start') 

    async def init_state(self, time) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_init', 
                                time=time) 

    async def ready_state(self, ctx) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_ready', 
                                ctx=ctx) 

    async def house_join(self, ctx, house) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_house_add', 
                                ctx=ctx, house=house) 

    async def house_exit(self, ctx, house) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_house_remove', 
                                ctx=ctx, house=house) 

    async def house_down(self, ctx, house) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_house_downage', 
                                ctx=ctx, house=house) 

    async def house_member_enter(self, ctx, member) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_house_enter',
                                ctx=ctx, member=member) 

    async def house_member_exit(self, ctx, member) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_house_exit',
                                ctx=ctx, member=member) 

    async def presence_update(self, precence, member) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_presence_update',
                                precence=precence, member=member) 

    async def message_create(self, message) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_message_create',
                                message=message) 

    async def message_delete(self, message) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_message_delete',
                                message=message) 

    async def message_update(self, message) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_message_update',
                                message=message) 

    async def typing_start(self, member) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_typing_start',
                                member=member) 

    async def typing_end(self, member) -> None:
        await dispatch_func_if_exists(obj=self.call_obj, func_name='on_typing_end',
                                member=member) 
