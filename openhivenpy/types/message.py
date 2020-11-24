from datetime import datetime
import logging
import sys
import asyncio

from ._get_type import getType
import openhivenpy.exceptions as errs
from openhivenpy.gateway.http import HTTPClient

logger = logging.getLogger(__name__)

class DeletedMessage():
    """`openhivenpy.types.DeletedMessage`
    
    Data Class for a removed Hiven message
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    The class inherits all the avaible data from Hiven(attr -> read-only)!
    
    Returned with on_message_delete()
    
    Attributes
    ~~~~~~~~~~
    
    house_id: `int` - ID of the House where the message was deleted
    
    message_id: `int` - ID of the message that was deleted
    
    room_id: `int` - ID of the Room where the message was deleted
    
    """
    def __init__(self, data: dict):
        self._message_id = int(data.get('message_id'))
        self._house_id = int(data.get('house_id'))
        self._room_id =  int(data.get('room_id'))

    @property
    def message_id(self):
        return int(self._message_id)

    @property
    def house_id(self):
        return int(self._house_id)

    @property
    def room_id(self):
        return int(self._room_id)
    

class Message():
    """`openhivenpy.types.Message`
    
    Data Class for a standard Hiven message
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    The class inherits all the avaible data from Hiven(attr -> read-only)!
    
    Returned with room message list and House.get_message()
 
    Attributes
    ~~~~~~~~~~
    
    id: `int` - ID of the Message
    
    content: `str` - Simple string content of the message
    
    author: `openhivenpy.types.User` - Author Object
    
    author_id: `int` - ID of the Author that created the message
    
    room: `openhivenpy.types.Room` - Room where the message was sent
    
    room_id: `int` - ID of the Room where the message was deleted
    
    house: `openhivenpy.types.House` - House where the message was sent
    
    house_id: `int` - ID of the House where the message was deleted
    
    created_at: `datetime.datetime` - Creation timestamp
    
    edited_at: `datetime.datetime` - If edited returns a string timestamp else None
    
    attatchment: `str` - In work
    
    mentions: `User` - A list of Users that were mentioned in the message
    
    exploding: `None` - In work
    
    """
    def __init__(self, data: dict, http_client: HTTPClient, house, room, author):
        try:
            id = data.get('id', 0)
            self._id = int(id) if data.get('id') != None else None
            self._author = author
            self._attatchment = data.get('attatchment')
            self._content = data.get('content')
            # Converting to seconds because it's in miliseconds
            self._timestamp = datetime.fromtimestamp(int(data.get('timestamp')) / 1000) if data.get('timestamp') != None else None
            self._edited_at = data.get('edited_at')
            self._mentions = [getType.Member(x, http_client, house) for x in data.get('mentions', [])]
            self._type = data.get('type') # I believe, 0 = normal message, 1 = system.
            self._exploding = data.get('exploding')
            self._house_id = data.get('house_id')
            
            self._house_id = int(data.get('house_id')) if data.get('house_id') != None else None
            self._house = house
            self._room_id = int(data.get('room_id')) if data.get('room_id') != None else None
            self._room = room 
            
            self._embed = getType.Embed(data.get('embed')) if data.get('embed') != None else None
            
            self._http_client = http_client
            
        except AttributeError as e: 
            logger.error(f"Unable to initialize the Message object! Cause of Error: {str(e)}")
            raise errs.FaultyInitialization("The data of the object Message is not in correct Format")
        
        except Exception as e: 
            logger.error(f"Unable to initialize the Message object! Cause of Error: {str(e)}")
            raise sys.exc_info()[1](e)

    @property
    def id(self):
        return int(self._id)

    @property
    def author(self):
        return self._author

    @property
    def created_at(self):
        return self._timestamp

    @property
    def edited_at(self):
        return self._edited_at

    @property
    def room(self):
        return self._room

    @property
    def house(self):
        return self._house

    @property
    def attatchment(self):
        return self._attatchment

    @property
    def content(self):
        return self._content

    @property
    def mentions(self):
        return self._mentions

    @property
    def room_id(self):
        return self._room_id

    @property
    def house_id(self):
        return self._house_id

    @property 
    def embed(self):
        return self._embed

    async def mark_message_as_read(self, delay: float) -> bool:
        """`openhivenpy.types.Message.ack`

        Marks the message as read. This doesn't need to be done for bot clients. 
        
        Returns `True` if successful.
        
        """
        try:
            response = await self._http_client.delete(endpoint=f"/rooms/{self.room_id}/messages/{self.id}/ack")
            await asyncio.sleep(delay=delay)
            return True
        
        except Exception as e:
            raise sys.exc_info()[1](e)

    async def delete(self, delay: float) -> bool:
        """`openhivenpy.types.Message.delete()`

        Deletes the message. Raises Forbidden if not allowed. 
        
        Returns a DeletedMessage Object if successful
        
        """
        try:
            response = await self._http_client.delete(endpoint=f"/rooms/{self.room_id}/messages/{self.id}")
            await asyncio.sleep(delay=delay)
            msg = DeletedMessage(response.json(), self._http_client)
            return msg
        
        except Exception as e:
            raise sys.exc_info()[1](e)
        