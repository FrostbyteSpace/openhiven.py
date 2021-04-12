# Used for type hinting and not having to use annotations for the objects
from __future__ import annotations

import logging
import sys
import typing
import fastjsonschema

from . import HivenTypeObject, check_valid
from . import House
from .. import utils
from ..exceptions import InitializationError, InvalidPassedDataError

# Only importing the Objects for the purpose of type hinting and not actual use
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .. import HivenClient

logger = logging.getLogger(__name__)

__all__ = ['Invite']


class Invite(HivenTypeObject):
    """ Represents an Invite to a Hiven House """
    json_schema = {
        'type': 'object',
        'properties': {
            'code': {
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'null'}
                ],
            },
            'url': {
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'null'}
                ],
            },
            'created_at': {
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'null'}
                ],
                'default': None
            },
            'house_id': {
                'anyOf': [
                    {'type': 'string'},
                    {'type': 'null'}
                ],
                'default': None
            },
            'blocked': {
                'anyOf': [
                    {'type': 'boolean'},
                    {'type': 'null'}
                ],
                'default': None
            },
            'max_age': {
                'anyOf': [
                    {'type': 'integer'},
                    {'type': 'null'}
                ],
                'default': None
            },
            'max_uses': {
                'anyOf': [
                    {'type': 'integer'},
                    {'type': 'null'}
                ],
                'default': None
            },
            'mfa_enabled': {
                'anyOf': [
                    {'type': 'boolean'},
                    {'type': 'null'}
                ],
                'default': None
            },
            'type': {
                'type': 'integer',
                'default': None
            },
            'house_members': {
                'type': 'integer',
                'default': None
            }
        },
        'additionalProperties': False,
        'required': ['code']
    }
    json_validator = fastjsonschema.compile(json_schema)

    def __init__(self, data: dict, client: HivenClient):
        try:
            self._code = data.get('code')
            self._url = data.get('url')
            self._created_at = data.get('created_at')
            self._house_id = data.get('house_id')
            self._max_age = data.get('max_age')
            self._max_uses = data.get('max_uses')
            self._type = data.get('type')
            self._house = data.get('house')
            self._house_members = data.get('house_members')

        except Exception as e:
            utils.log_traceback(
                msg=f"Traceback in function '{self.__class__.__name__}' Validation:",
                suffix=f"Failed to initialise {self.__class__.__name__} due to exception:\n"
                       f"{sys.exc_info()[0].__name__}: {e}!"
            )
            raise InitializationError(
                f"Failed to initialise {self.__class__.__name__} due to an exception occurring"
            ) from e
        else:
            self._client = client

    def __repr__(self) -> str:
        info = [
            ('code', self.code),
            ('url', self.url),
            ('created_at', self.created_at),
            ('house_id', self.house_id),
            ('type', self.type),
            ('max_age', self.max_age),
            ('max_uses', self.max_uses),
        ]
        return '<Invite {}>'.format(' '.join('%s=%s' % t for t in info))

    @classmethod
    @check_valid
    def format_obj_data(cls, data: dict) -> dict:
        """
        Validates the data and appends data if it is missing that would be required for the creation of an
        instance.

        ---

        Does NOT contain other objects and only their ids!

        :param data: Data that should be validated and used to form the object
        :return: The modified dictionary, which can then be used to create a new class instance
        """
        if data.get('invite') is not None:
            invite = data.get('invite')
        else:
            invite = data
        data['code'] = invite.get('code')
        data['url'] = "https://hiven.house/{}".format(data['code'])
        data['created_at'] = invite.get('created_at')
        data['max_age'] = invite.get('max_age')
        data['max_uses'] = invite.get('max_uses')
        data['type'] = invite.get('type')
        data['house_members'] = data.get('counts', {}).get('house_members')

        if not invite.get('house_id') and invite.get('house'):
            house = invite.pop('house')
            if type(house) is dict:
                house_id = house.get('id')
            elif isinstance(house, HivenTypeObject):
                house_id = getattr(house, 'id', None)
            else:
                house_id = None

            if house_id is None:
                raise InvalidPassedDataError("The passed house is not in the correct format!", data=data)
            else:
                data['house_id'] = house_id

        data = cls.validate(data)
        data['type'] = int(data['type'])
        data['house'] = data['house_id']
        return data

    @property
    def code(self) -> int:
        return getattr(self, '_code', None)

    @property
    def url(self) -> str:
        return getattr(self, '_url', None)
    
    @property
    def house_id(self) -> str:
        return getattr(self, '_house_id', None)
    
    @property
    def max_age(self) -> int:
        return getattr(self, '_max_age', None)

    @property
    def max_uses(self) -> int:
        return getattr(self, '_max_uses', None)
    
    @property
    def type(self) -> int:
        return getattr(self, '_type', None)
        
    @property
    def house(self) -> typing.Optional[House]:
        from . import House
        if type(self._house) is str:
            house_id = self._house
        elif type(self.house_id) is str:
            house_id = self.house_id
        else:
            house_id = None

        if house_id:
            data = self._client.storage['houses'].get(house_id)
            if data:
                self._house = House(data=data, client=self._client)
                return self._house
            else:
                return None

        elif type(self._house) is House:
            return self._house
        else:
            return None
    
    @property
    def house_members(self) -> int:
        return getattr(self, '_house_members', None)

    @property
    def created_at(self) -> str:
        return getattr(self, '_created_at', None)
