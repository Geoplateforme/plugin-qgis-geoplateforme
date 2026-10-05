# standard
import json
import math
import re
from typing import List

# PyQGIS
from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    DeleteUserPermissionException,
    ReadUserPermissionException,
)
from geoplateforme.api.permissions import Permission
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


class UserPermissionRequestManager:
    MAX_LIMIT = 50

    def get_base_url(self) -> str:
        """Get base url for user permissions

        :return: url for user permissions
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/users/me/permissions"

    def __init__(self):
        """Helper for stored_data request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_user_permission_list(self) -> List[Permission]:
        """Get list of user permission

        :raises ReadUserPermissionException: when error occur during requesting the API

        :return: list of available user permission
        :rtype: List[Permission]
        """
        self.log(f"{__name__}.get_user_permission_list()")

        nb_value = self._get_nb_available_user_permission()
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(nb_request):
            result += self._get_user_permission_list(page + 1, self.MAX_LIMIT)
        return result

    def _get_user_permission_list(
        self,
        page: int = 1,
        limit: int = MAX_LIMIT,
    ) -> List[Permission]:
        """Get list of user permission

        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int

        :raises ReadUserPermissionException: when error occur during requesting the API

        :return: list of available user permission
        :rtype: List[Permission]
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url()}?page={page}&limit={limit}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadUserPermissionException(
                f"Error while fetching user permission : {err}"
            )

        data = json.loads(reply.data())
        return [Permission.from_dict(datastore_id="", val=val) for val in data]

    def _get_nb_available_user_permission(
        self,
    ) -> int:
        """Get number of available user permission

        :raises ReadUserPermissionException: when error occur during requesting the API

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
            raise ReadUserPermissionException(
                f"Error while fetching user permission : {err}"
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
            raise ReadUserPermissionException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def get_user_permission(self, user_permission_id: str) -> Permission:
        """Get user permission by id

        :param user_permission_id: user permission id
        :type user_permission_id: str

        :raises ReadUserPermissionException: when error occur during requesting the API

        :return: user permission
        :rtype: Permission
        """
        self.log(
            f"{__name__}.get_user_permission(user_permission_id:{user_permission_id})"
        )
        return Permission.from_dict(
            datastore_id="", val=self.get_user_permission_json(user_permission_id)
        )

    def get_user_permission_json(self, user_permission_id: str) -> dict:
        """Get dict values of user permission

        :param user_permission_id: user permission id
        :type user_permission_id: str

        :raises ReadUserPermissionException: when error occur during requesting the API

        :return: dict values of user permission
        :rtype: dict
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url()}/{user_permission_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return json.loads(reply.data())
        except ConnectionError as err:
            raise ReadUserPermissionException(
                f"Error while fetching user permission : {err}"
            )

    def delete(self, user_permission_id: str) -> None:
        """Delete a user permission.

        :param user_permission_id: user permission id
        :type user_permission_id: str

        :raises DeleteUserPermissionException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete(user_permission_id:{user_permission_id})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url()}/{user_permission_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteUserPermissionException(
                f"Error while deleting user permission: {err}."
            )
