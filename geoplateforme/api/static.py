import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    StaticFileUploadException,
    UnavailableStaticException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


class StaticType(Enum):
    GEOSERVER_FTL = "GEOSERVER-FTL"
    GEOSERVER_STYLE = "GEOSERVER-STYLE"
    ROK4_STYLE = "ROK4-STYLE"
    DERIVATION_SQL = "DERIVATION-SQL"


@dataclass
class Static:
    _id: str
    datastore_id: str
    name: str
    type_static: StaticType
    description: str = ""

    @classmethod
    def from_dict(cls, datastore_id: str, val: dict):
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
            name=val["name"],
            type_static=StaticType(val["type"]),
        )
        if "description" in val:
            res.description = val["description"]


class StaticRequestManager:
    MAX_LIMIT = 50

    def __init__(self):
        """Helper for stored_data request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore_id: str) -> str:
        """Get base url for static for a datastore

        :param datastore_id: datastore id
        :type datastore_id: str

        :return: url for static
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore_id}/statics"

    def get_static(self, datastore_id: str, static_id: str) -> Static:
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{static_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableStaticException(f"Error while fetching static : {err}")

        data = json.loads(reply.data())
        return Static.from_dict(datastore_id, data)

    def create_static(
        self,
        datastore_id: str,
        file_path: Path,
        name: str,
        static_type: StaticType,
        description: str,
    ) -> str:
        self.log(
            f"{__name__}.create_static(datastore:{datastore_id}, file_path: {file_path})"
        )

        try:
            data = {
                "name": name,
                "type": static_type.value,
            }
            if description:
                data["description"] = description
            reply = self.request_manager.post_file(
                url=QUrl(f"{self.get_base_url(datastore_id)}"),
                config_id=self.plg_settings.qgis_auth_id,
                file_path=file_path,
                data=data,
            )
        except ConnectionError as err:
            raise StaticFileUploadException(f"Error while posting upload file : {err}")

        data = json.loads(reply.data())
        return data["_id"]
