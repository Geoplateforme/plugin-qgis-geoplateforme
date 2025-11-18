#! python3

# Standard library
from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from typing import Optional

# PyQGIS
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

# project
from geoplateforme.api.custom_exceptions import UnavailableUserException
from geoplateforme.api.utils import as_localized_datetime
from geoplateforme.toolbelt.log_handler import PlgLogger
from geoplateforme.toolbelt.preferences import PlgOptionsManager

logger = logging.getLogger(__name__)


@dataclass
class Community:
    _id: str
    public: bool
    name: str
    technical_name: str
    supervisor: Optional[str] = None
    datastore: Optional[str] = None

    @classmethod
    def from_dict(cls, val: dict) -> Community:
        """Load object from a dict.
        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: Community
        """
        res = cls(
            _id=val["_id"],
            public=val["public"],
            name=val["name"],
            technical_name=val["technical_name"],
        )
        if "datastore" in val:
            res.datastore = val["datastore"]

        if "supervisor" in val:
            res.datastore = val["supervisor"]
        return res


@dataclass
class CommunitiesMember:
    rights: {}
    community: Community

    @classmethod
    def from_json(cls, data):
        res = cls(rights=data["rights"], community=Community(**data["community"]))
        return res


@dataclass
class Datastore:
    id: str
    name: str


@dataclass
class User:
    _id: str
    first_name: str
    last_name: str
    email: str
    creation: datetime
    communities_member: list[CommunitiesMember]

    def get_datastore_list(self) -> list[Datastore]:
        """
        Get datastore list from communities

        Returns: [Datastore] datastore list

        """
        result = []
        for community_member in self.communities_member:
            if community_member.community.datastore:
                result.append(
                    Datastore(
                        id=community_member.community.datastore,
                        name=community_member.community.name,
                    )
                )
        return result

    def get_community_list(self) -> list[Community]:
        """Get list of available community

        :return: community list
        :rtype: list[Community]
        """
        return [member.community for member in self.communities_member]

    @classmethod
    def from_json(cls, data):
        """
        Define User from json data

        Args:
            data: json data

        Returns: User

        """
        if "first_name" not in data:
            data["first_name"] = None
        if "last_name" not in data:
            data["last_name"] = None
        res = cls(
            _id=data["_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            creation=data["creation"],
            communities_member=[],
        )
        for communities in data["communities_member"]:
            res.communities_member.append(CommunitiesMember.from_json(communities))
        return res

    @property
    def creation_as_localized_datetime(self) -> str:
        """Try to convert raw creation date as localized datetime using Qt.

        :return: localized date time (or raw creation string if conversion fails)
        :rtype: str
        """
        return as_localized_datetime(self.creation)


class UserRequestsManager:
    def __init__(self):
        """
        Helper for user request

        """
        self.log = PlgLogger().log
        self.ntwk_requester_blk = QgsBlockingNetworkRequest()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self) -> str:
        """
        Get base url for user

        Returns: url for user

        """
        return f"{self.plg_settings.base_url_api_entrepot}/users"

    def get_user(self) -> User:
        """Get user.

        Returns: User, raise UnavailableUserException otherwise
        """
        self.log(f"{__name__}.get_user()")

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(f"{self.get_base_url()}/me"))

        # headers
        req.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        # send request
        resp = self.ntwk_requester_blk.get(req, forceRefresh=True)

        # check response
        if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise UnavailableUserException(
                f"Error while fetching user info : {self.ntwk_requester_blk.errorMessage()}"
            )

        # check response
        req_reply = self.ntwk_requester_blk.reply()
        if not req_reply.rawHeader(b"Content-Type") == "application/json":
            raise UnavailableUserException(
                "Response mime-type is '{}' not 'application/json' as required.".format(
                    req_reply.rawHeader(b"Content-type")
                )
            )

        data = json.loads(req_reply.content().data())
        return User.from_json(data)

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)
