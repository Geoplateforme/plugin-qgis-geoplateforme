#! python3

# Standard library
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import List

from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    DeleteKeyAccessException,
    DeleteUserKeyAccessesException,
    ReadKeyAccessException,
)
from geoplateforme.api.offerings import Offering
from geoplateforme.api.permissions import Permission
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


@dataclass
class KeyAccess:
    _id: str
    key_id: str
    permission: Permission
    offering: Offering

    @classmethod
    def from_dict(cls, key_id: str, val: dict) -> KeyAccess:
        """Load object from a dict.

        :param key_id: key id
        :type key_id: str
        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: StoredData
        """
        res = cls(
            _id=val["_id"],
            key_id=key_id,
            permission=Permission.from_dict(datastore_id="", val=val["permission"]),
            offering=Offering.from_dict(datastore_id="", val=val["offering"]),
        )
        return res


class KeyAccessRequestManager:
    MAX_LIMIT = 50

    def get_base_url(self, user_key_id: str) -> str:
        """Get base url for user keys

        :param user_key_id: user key id
        :type user_key_id: str

        :return: url for user keys
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/users/me/keys/{user_key_id}/accesses"

    def __init__(self):
        """Helper for user key access request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_key_access_list(self, user_key_id: str) -> List[KeyAccess]:
        """Get list of user key access

        :param user_key_id: user key id
        :type user_key_id: str

        :raises ReadKeyAccessException: when error occur during requesting the API

        :return: list of available user key access
        :rtype: List[KeyAccess]
        """
        self.log(f"{__name__}.get_key_access_list({user_key_id=})")

        nb_value = self._get_nb_available_access(user_key_id)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_key_access_list(user_key_id, page + 1, self.MAX_LIMIT)
        return result

    def _get_key_access_list(
        self,
        user_key_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
    ) -> List[KeyAccess]:
        """Get list of user key

        :param user_key_id: user key id
        :type user_key_id: str
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
                url=QUrl(f"{self.get_base_url(user_key_id)}?page={page}&limit={limit}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadKeyAccessException(f"Error while fetching user key : {err}")

        data = json.loads(reply.data())
        return [KeyAccess.from_dict(key_id=user_key_id, val=val) for val in data]

    def _get_nb_available_access(self, user_key_id: str) -> int:
        """Get number of available user key access

        :param user_key_id: user key id
        :type user_key_id: str

        :raises ReadUserKeyException: when error occur during requesting the API

        :return: number of available data
        :rtype: int
        """
        # For now read with maximum limit possible
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(user_key_id)}?limit=1"),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadKeyAccessException(
                f"Error while fetching user key access : {err}"
            )

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadKeyAccessException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def delete(self, user_key_id: str, access_id: str) -> None:
        """Delete a user access key.

        :param user_key_id: user key id
        :type user_key_id: str
        :param access_id: user key id
        :type access_id: str

        :raises ReadUserKeyException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete({user_key_id=},{access_id=})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url(user_key_id)}/{access_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteKeyAccessException(
                f"Error while deleting user key access: {err}."
            )

    def delete_user_key_accesses(self, user_key_id: str) -> None:
        """Delete accesses for a user key

        :param user_key_id: user key id
        :type user_key_id: str
        :raises DeleteKeyAccessesException: Error when deleting user key accesses
        """
        self.log(f"{__name__}.delete_user_key_accesses({user_key_id=})")
        try:
            # Get all available accesses
            accesses = self.get_key_access_list(user_key_id=user_key_id)

            # Delete all available accesses
            for access in accesses:
                self.delete(user_key_id=user_key_id, access_id=access._id)
        except (ReadKeyAccessException, DeleteKeyAccessException) as err:
            raise DeleteUserKeyAccessesException(
                f"Error user key access delete : {err}"
            )
