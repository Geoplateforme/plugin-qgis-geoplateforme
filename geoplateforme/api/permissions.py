#! python3

# Standard library
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from qgis.PyQt.QtCore import QByteArray, QDateTime, Qt, QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    CreatePermissionException,
    DeletePermissionException,
    ReadPermissionException,
    UpdatePermissionException,
)
from geoplateforme.api.offerings import Offering
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


@dataclass
class PermissionDatastoreAuthor:
    _id: str
    name: Optional[str] = None
    technical_name: Optional[str] = None
    active: Optional[bool] = None


class PermissionType(Enum):
    ACCOUNT = "ACCOUNT"
    COMMUNITY = "COMMUNITY"


@dataclass
class PermissionAccountBeneficiary:
    _id: str
    last_name: Optional[str] = None
    first_name: Optional[str] = None


@dataclass
class PermissionCommunityBeneficiary:
    _id: str
    name: str
    technical_name: str
    contact: Optional[str] = None
    public: Optional[bool] = None


@dataclass
class Permission:
    _id: str
    datastore_id: str
    licence: str
    offerings: Optional[list[Offering]] = None
    end_date: Optional[datetime] = None
    datastore_author: Optional[PermissionDatastoreAuthor] = None
    beneficiary: Optional[
        PermissionAccountBeneficiary | PermissionCommunityBeneficiary
    ] = None
    only_oauth: Optional[bool] = None

    @property
    def local_end_date(self) -> Optional[QDateTime]:
        """Get end date with current local

        :return: end date with current local, None if no end date
        :rtype: Optional[QDateTime]
        """
        if self.end_date:
            qt_date = QDateTime(
                self.end_date.date(),
                self.end_date.time(),
                Qt.TimeSpec.UTC,
            )
            qt_date = qt_date.toLocalTime()
            return qt_date
        return None

    @classmethod
    def from_dict(cls, datastore_id: str, val: dict) -> Permission:
        """Load object from a dict.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: StoredData
        """
        res = cls(
            _id=val["_id"],
            datastore_id=datastore_id,
            licence=val["licence"],
        )
        if "offerings" in val:
            res.offerings = [
                Offering.from_dict(datastore_id=datastore_id, val=offer)
                for offer in val["offerings"]
            ]

        if "end_date" in val:
            try:
                res.end_date = datetime.fromisoformat(val["end_date"])
            except ValueError:
                res.end_date = None
        if "datastore_author" in val:
            res.datastore_author = PermissionDatastoreAuthor(**val["datastore_author"])
        if "beneficiary" in val:
            value = val["beneficiary"]
            if "technical_name" in value:
                res.beneficiary = PermissionCommunityBeneficiary(**value)
            else:
                res.beneficiary = PermissionAccountBeneficiary(**value)
        if "only_oauth" in val:
            res.only_oauth = val["only_oauth"]
        return res


class PermissionRequestManager:
    MAX_LIMIT = 50

    def __init__(self):
        """Helper for permission request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore_id: str) -> str:
        """Get base url for permissions

        :param datastore_id: datastore id
        :type datastore_id: str

        :return: url for datastore permission
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore_id}/permissions"

    def get_permission_list(
        self, datastore_id: str, offering_id: Optional[str] = None
    ) -> List[Permission]:
        """Get list of permission for an offering

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering_id: offering id
        :type offering_id: Optional[str]

        :raises ReadPermissionException: when error occur during requesting the API

        :return: list of available permission
        :rtype: List[Permission]
        """
        self.log(f"{__name__}.get_permission_list({datastore_id=},{offering_id=})")

        nb_value = self._get_nb_available_permission(datastore_id, offering_id)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_permission_list(
                datastore_id, page + 1, self.MAX_LIMIT, offering_id
            )
        return result

    def _get_permission_list(
        self,
        datastore_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
        offering_id: Optional[str] = None,
    ) -> List[Permission]:
        """Get list of permission

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering_id: offering id
        :type offering_id: Optional[str]
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int

        :raises ReadPermissionException: when error occur during requesting the API

        :return: list of available permission
        :rtype: List[Permission]
        """
        if offering_id:
            offering_filter = f"&offering={offering_id}"
        else:
            offering_filter = ""
        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}?page={page}&limit={limit}{offering_filter}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadPermissionException(f"Error while fetching permission : {err}")

        data = json.loads(reply.data())
        return [Permission.from_dict(datastore_id, val) for val in data]

    def _get_nb_available_permission(
        self, datastore_id: str, offering_id: Optional[str] = None
    ) -> int:
        """Get number of available permission

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering_id: offering id
        :type offering_id: Optional[str]

        :raises ReadPermissionException: when error occur during requesting the API

        :return: number of available data
        :rtype: int
        """
        if offering_id:
            offering_filter = f"&offering={offering_id}"
        else:
            offering_filter = ""
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}?limit=1{offering_filter}"),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadPermissionException(f"Error while fetching permission : {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadPermissionException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def delete(self, datastore_id: str, permission_id: str) -> None:
        """Delete a permission.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param permission_id: permission id
        :type permission_id: str

        :raises DeletePermissionException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete({datastore_id=},{permission_id=})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{permission_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeletePermissionException(f"Error while deleting permission: {err}.")

    def create_permission(
        self,
        datastore_id: str,
        licence: str,
        permission_type: PermissionType,
        users_or_communities: List[str],
        offerings: List[str],
        end_date: Optional[datetime] = None,
        only_oauth: Optional[bool] = None,
    ) -> List[Permission]:
        """Create a permission

        :param datastore_id: datastore id
        :type datastore_id: str
        :param licence: licence
        :type licence: str
        :param permission_type: permission type
        :type permission_type: PermissionType
        :param users_or_communities: list of user or communities (depends on permission type)
        :type users_or_communities: List[str]
        :param offerings: list of offering for permission
        :type offerings: List[str]
        :param end_date: end date, defaults to None
        :type end_date: Optional[datetime], optional
        :param only_oauth: authorize only OAuth2 key, defaults to None
        :type only_oauth: Optional[bool], optional
        :raises CreatePermissionException: error during creation
        :return: list of created permission. One permission for each user or community
        :rtype: List[Permission]
        """
        self.log(
            f"{__name__}.create_permission({datastore_id=},{licence=},{permission_type=},{users_or_communities=},{offerings=},{end_date=},{only_oauth=})"
        )
        try:
            # encode data
            data = QByteArray()
            data_map = {
                "licence": licence,
                "offerings": offerings,
                "type": permission_type.value,
            }
            if permission_type == PermissionType.ACCOUNT:
                data_map["users"] = users_or_communities
            else:
                data_map["communities"] = users_or_communities

            if end_date:
                data_map["end_date"] = f"{end_date.isoformat()}Z"
            if only_oauth:
                data_map["only_oauth"] = only_oauth

            data.append(json.dumps(data_map).encode("utf-8"))
            reply = self.request_manager.post_url(
                url=QUrl(self.get_base_url(datastore_id)),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise CreatePermissionException(f"Error in permission creation : {err}")
        # check response type
        data = json.loads(reply.data())
        return [
            Permission.from_dict(datastore_id, permission_data)
            for permission_data in data
        ]

    def update_permission(
        self,
        datastore_id: str,
        permission_id: str,
        licence: str,
        offerings: List[str],
        end_date: Optional[datetime] = None,
    ) -> None:
        """Update a permission

        :param datastore_id: datastore id
        :type datastore_id: str
        :param permission_id: permission id
        :type permission_id: str
        :param licence: licence
        :type licence: str
        :param offerings: list of offering for permission
        :type offerings: List[str]
        :param end_date: end date, defaults to None
        :type end_date: Optional[datetime], optional
        :raises UpdatePermissionException: error during update
        """
        self.log(
            f"{__name__}.update_permission({datastore_id=},{permission_id=},{licence=},{offerings=},{end_date=})"
        )
        try:
            # encode data
            data = QByteArray()
            data_map = {
                "licence": licence,
                "offerings": offerings,
            }

            if end_date:
                data_map["end_date"] = f"{end_date.isoformat()}Z"

            data.append(json.dumps(data_map).encode("utf-8"))
            self.request_manager.patch_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{permission_id}"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise UpdatePermissionException(f"Error in permission update : {err}")
