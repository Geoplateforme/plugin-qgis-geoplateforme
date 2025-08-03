# standard
import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

# PyQGIS
from qgis.core import QgsApplication, QgsAuthMethodConfig
from qgis.PyQt.QtCore import QByteArray, QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    CreateAccessesException,
    CreateUserKeyException,
    DeleteUserKeyException,
    ReadUserKeyException,
    UpdateUserKeyException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager

CFG_AUTH_PREFIX = "gpf_"


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
    def from_dict(cls, val: dict) :
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

    @staticmethod
    def create_hash_auth_config(name: str, hash_val: str) -> QgsAuthMethodConfig:
        """Create QgsAuthMethodConfig for hash authentification with apikey

        :param name: name of configuration
        :type name: str
        :param hash_val: hash value
        :type hash_val: str
        :return: created configuration. Warning: config must be added to QgsApplication.authManager() before use
        :rtype: QgsAuthMethodConfig
        """
        new_auth_config = QgsAuthMethodConfig(method="APIHeader", version=2)
        new_auth_config.setId(QgsApplication.authManager().uniqueConfigId())
        new_auth_config.setName(f"{CFG_AUTH_PREFIX}{name}")
        new_auth_config.setConfigMap({"apikey": hash_val})
        return new_auth_config

    @staticmethod
    def create_basic_auth_config(
        name: str, user: str, password: str
    ) -> QgsAuthMethodConfig:
        """Create QgsAuthMethodConfig for basic authentification with username / password

        :param name: name of configuration
        :type name: str
        :param user: username
        :type user: str
        :param password: password
        :type password: str
        :return: created configuration. Warning: config must be added to QgsApplication.authManager() before use
        :rtype: QgsAuthMethodConfig
        """
        new_auth_config = QgsAuthMethodConfig(method="Basic", version=2)
        new_auth_config.setId(QgsApplication.authManager().uniqueConfigId())
        new_auth_config.setName(f"{CFG_AUTH_PREFIX}{name}")
        new_auth_config.setConfigMap(
            {"password": password, "realm": "", "username": user}
        )
        return new_auth_config


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

        :raises DeleteUserKeyException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete(user_key_id:{user_key_id})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url()}/{user_key_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteUserKeyException(f"Error while deleting user key: {err}.")

    def create_user_key(
        self,
        name: str,
        user_key_type: UserKeyType,
        type_infos: dict,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> UserKey:
        """Create a use key

        :param name: key name
        :type name: str
        :param user_key_type: key type
        :type user_key_type: UserKeyType
        :param type_infos: key type infos (depends on key type)
        :type type_infos: dict
        :param whitelist: list of whitelist IPs, defaults to None
        :type whitelist: Optional[List[str]], optional
        :param blacklist: list of blacklist IPs, defaults to None
        :type blacklist: Optional[List[str]], optional
        :param user_agent: user agent, defaults to None
        :type user_agent: Optional[str], optional
        :param referer: referer, defaults to None
        :type referer: Optional[str], optional
        :raises CreateUserKeyException: Error when creating key
        :return: created key
        :rtype: UserKey
        """
        self.log(
            f"{__name__}.create_user_key({name=},{user_key_type=},{type_infos=},{whitelist=},{blacklist=},{user_agent=},{referer=})"
        )
        try:
            # encode data
            data = QByteArray()
            data_map = {
                "name": name,
                "type": user_key_type.value,
                "type_infos": type_infos,
            }
            if whitelist:
                data_map["whitelist"] = whitelist
            if blacklist:
                data_map["blacklist"] = blacklist
            if user_agent:
                data_map["user_agent"] = user_agent
            if referer:
                data_map["referer"] = referer

            data.append(json.dumps(data_map))
            reply = self.request_manager.post_url(
                url=QUrl(self.get_base_url()),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise CreateUserKeyException(f"Error in user key creation : {err}")
        # check response type
        data = json.loads(reply.data())
        return UserKey.from_dict(data)

    def update_user_key(
        self,
        user_key_id: str,
        name: str,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> None:
        """Update a user key

        :param user_key_id: user key id
        :type user_key_id: str
        :param name: key name
        :type name: str
        :param whitelist: list of whitelist IPs, defaults to None
        :type whitelist: Optional[List[str]], optional
        :param blacklist: list of blacklist IPs, defaults to None
        :type blacklist: Optional[List[str]], optional
        :param user_agent: user agent, defaults to None
        :type user_agent: Optional[str], optional
        :param referer: referer, defaults to None
        :type referer: Optional[str], optional
        :raises UpdateUserKeyException: Error when updating key
        """
        self.log(
            f"{__name__}.update_user_key({name=},{user_key_id=},{whitelist=},{blacklist=},{user_agent=},{referer=})"
        )
        try:
            # encode data
            data = QByteArray()
            data_map = {
                "name": name,
            }
            if whitelist is not None:
                data_map["whitelist"] = whitelist
            if blacklist is not None:
                data_map["blacklist"] = blacklist
            if user_agent:
                data_map["user_agent"] = user_agent
            if referer:
                data_map["referer"] = referer

            data.append(json.dumps(data_map))
            self.request_manager.patch_url(
                url=QUrl(f"{self.get_base_url()}/{user_key_id}"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise UpdateUserKeyException(f"Error in user key update : {err}")

    def create_accesses(
        self, user_key_id: str, permission_id: str, offering_ids: list[str]
    ) -> None:
        """Create accesses for a user key for a permission and a list of offering

        :param user_key_id: user key id
        :type user_key_id: str
        :param permission_id: permission id
        :type permission_id: str
        :param offering_ids: offering ids list
        :type offering_ids: list[str]
        :raises CreateAccessesException: Error when creating accesses
        """
        self.log(
            f"{__name__}.create_accesses({user_key_id=},{permission_id=},{offering_ids=})"
        )
        try:
            # encode data
            data = QByteArray()
            data_map = {"permission": permission_id, "offerings": offering_ids}

            data.append(json.dumps(data_map))
            self.request_manager.post_url(
                url=QUrl(f"{self.get_base_url()}/{user_key_id}/accesses"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise CreateAccessesException(f"Error in accesses creation : {err}")
