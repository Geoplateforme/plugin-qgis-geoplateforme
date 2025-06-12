import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Self

from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    DeleteUserKeyException,
    ReadUserKeyException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


class UserKeyType(Enum):
    HASH = "HASH"
    HEADER = "HEADER"
    BASIC = "BASIC"
    OAUTH2 = "OAUTH2"


@dataclass
class UserKey:
    _id: str
    name: str
    _type: UserKeyType

    is_detailed: bool = False
    # Optional
    _whitelist: Optional[list] = None
    _blacklist: Optional[list] = None
    _user_agent: Optional[list] = None
    _referer: Optional[list] = None
    _type_infos: Optional[dict] = None

    @property
    def whitelist(self) -> list:
        """Returns the whitelist of the user key.

        :return: user key whitelist
        :rtype: str
        """
        if not self._whitelist and not self.is_detailed:
            self.update_from_api()
        return self._whitelist

    @property
    def blacklist(self) -> list:
        """Returns the blacklist of the user key.

        :return: user key blacklist
        :rtype: dict
        """
        if not self._blacklist and not self.is_detailed:
            self.update_from_api()
        return self._blacklist

    @property
    def user_agent(self) -> list:
        """Returns the user_agent of the user key.

        :return: user key user_agent
        :rtype: str
        """
        if not self._user_agent and not self.is_detailed:
            self.update_from_api()
        return self._user_agent

    @property
    def referer(self) -> list:
        """Returns the referer of the user key.

        :return: user key referer
        :rtype: dict
        """
        if not self._referer and not self.is_detailed:
            self.update_from_api()
        return self._referer

    @property
    def type_infos(self) -> dict:
        """Returns the type_infos of the user key.

        :return: user key type_infos
        :rtype: dict
        """
        if not self._type_infos and not self.is_detailed:
            self.update_from_api()
        return self._type_infos

    def update_from_api(self):
        """Update the user key by calling API details."""
        manager = UserKeyRequestManager()
        data = manager.get_user_key_json(self._id)

        if "name" in data:
            self.name = data["name"]
        if "type" in data:
            self._type = UserKeyType(data["type"])
        if "whitelist" in data:
            self._whitelist = data["whitelist"]
        if "blacklist" in data:
            self._blacklist = data["blacklist"]
        if "user_agent" in data:
            self._user_agent = data["user_agent"]
        if "referer" in data:
            self._referer = data["referer"]
        if "type_infos" in data:
            self._type_infos = data["type_infos"]
        self.is_detailed = True

    @classmethod
    def from_dict(cls, val: dict) -> Self:
        """Load object from a dict.

        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: UserKey
        """
        res = cls(_id=val["_id"], name=val["name"], _type=UserKeyType(val["type"]))
        if "whitelist" in val:
            res._whitelist = val["whitelist"]
        if "blacklist" in val:
            res._blacklist = val["blacklist"]
        if "user_agent" in val:
            res._user_agent = val["user_agent"]
        if "referer" in val:
            res._referer = val["referer"]
        if "type_infos" in val:
            res._type_infos = val["type_infos"]

        return res


class UserKeyRequestManager:
    MAX_LIMIT = 50

    def get_base_url(self) -> str:
        """Get base url for user keys

        :return: url for user keys
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/users/me/keys"

    def __init__(self):
        """Helper for stored_data request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_user_key_list(self) -> List[UserKey]:
        """Get list of user key

        :raises ReadUserKeyException: when error occur during requesting the API

        :return: list of available user key
        :rtype: List[UserKey]
        """
        self.log(f"{__name__}.get_user_key_list()")

        nb_value = self._get_nb_available_user_key()
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_user_key_list(page + 1, self.MAX_LIMIT)
        return result

    def _get_user_key_list(
        self,
        page: int = 1,
        limit: int = MAX_LIMIT,
    ) -> List[UserKey]:
        """Get list of user key

        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int

        :raises ReadUserKeyException: when error occur during requesting the API

        :return: list of available user key
        :rtype: List[UserKey]
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url()}?page={page}&limit={limit}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadUserKeyException(f"Error while fetching user key : {err}")

        data = json.loads(reply.data())
        return [UserKey.from_dict(val) for val in data]

    def _get_nb_available_user_key(
        self,
    ) -> int:
        """Get number of available user key

        :raises ReadUserKeyException: when error occur during requesting the API

        :return: number of available data
        :rtype: int
        """
        # For now read with maximum limit possible
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url()}?limit=1"),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadUserKeyException(f"Error while fetching user key : {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadUserKeyException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def get_user_key(self, user_key_id: str) -> UserKey:
        """Get user key by id

        :param user_key_id: user key id
        :type user_key_id: str

        :raises ReadUserKeyException: when error occur during requesting the API

        :return: user key
        :rtype: UserKey
        """
        self.log(f"{__name__}.get_user_key(user_key_id:{user_key_id})")
        return UserKey.from_dict(self.get_user_key_json(user_key_id))

    def get_user_key_json(self, user_key_id: str) -> dict:
        """Get dict values of user key

        :param user_key_id: user key id
        :type user_key_id: str

        :raises ReadUserKeyException: when error occur during requesting the API

        :return: dict values of user key
        :rtype: dict
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url()}/{user_key_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return json.loads(reply.data())
        except ConnectionError as err:
            raise ReadUserKeyException(f"Error while fetching user key : {err}")

    def delete(self, user_key_id: str) -> None:
        """Delete a user key.

        :param user_key_id: user key id
        :type user_key_id: str

        :raises ReadUserKeyException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete(user_key_id:{user_key_id})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url()}/{user_key_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteUserKeyException(f"Error while deleting user key: {err}.")
