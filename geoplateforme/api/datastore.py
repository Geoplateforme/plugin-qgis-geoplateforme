# standard
import json
import logging
from dataclasses import dataclass

# PyQGIS
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

# project
from geoplateforme.api.custom_exceptions import (
    UnavailableDatastoreException,
    UnavailableEndpointException,
)
from geoplateforme.api.utils import qgs_blocking_get_request
from geoplateforme.toolbelt.log_handler import PlgLogger
from geoplateforme.toolbelt.preferences import PlgOptionsManager

logger = logging.getLogger(__name__)


@dataclass
class Datastore:
    id: str
    name: str
    technical_name: str
    storages: dict

    def get_storage_use_and_quota(self, storage_type: str) -> (int, int):
        """
        Get storage use and quota as tuple

        Args:
            storage_type: (str) storage type ("POSTGRESQL" or "FILESYSTEM" or "S3")

        Returns: (int,int) (use/quota)

        """
        result = (0, 0)
        for data in self.storages["data"]:
            if data["type"] == storage_type:
                result = (data["use"], data["quota"])
                break
        return result

    def get_upload_use_and_quota(self) -> (int, int):
        """
        Get upload use and quota as tuple

        Returns: (int,int) (use/quota)

        """
        result = (0, 0)
        if "uploads" in self.storages:
            result = (
                self.storages["uploads"]["use"],
                self.storages["uploads"]["quota"],
            )
        return result


class DatastoreRequestManager:
    def __init__(self):
        """
        Helper for datastore request

        """
        self.log = PlgLogger().log
        self.ntwk_requester_blk = QgsBlockingNetworkRequest()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore: str) -> str:
        """
        Get base url for endpoint

        Args:
            datastore: (str)

        Returns: url for Endpoint

        """
        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}"

    def get_datastore(self, datastore: str) -> Datastore:
        """
        Get datastore by id

        Args:
            datastore: (str) datastore id

        Returns: Datastore data, raise UnavailableDatastoreException otherwise
        """
        self.log(f"{__name__}.get_datastore(datastore:{datastore})")

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(self.get_base_url(datastore)))

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk,
            req,
            UnavailableDatastoreException,
            expected_type="application/json",
        )

        data = json.loads(req_reply.content().data())
        result = Datastore(
            id=data["_id"],
            name=data["name"],
            technical_name=data["technical_name"],
            storages=data["storages"],
        )
        return result

    def get_endpoint(self, datastore: str, data_type: str) -> str:
        """
        Get the endpoint for publication

        Args:
            datastore: (str)
            data_type: (str)

        Returns: first available endpoint id for data_type, raise UnavailableEndpointException otherwise
        """
        self.log(
            f"{__name__}.get_endpoint(datastore:{datastore},data_type:{data_type})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(self.get_base_url(datastore)))

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk,
            req,
            UnavailableEndpointException,
            expected_type="application/json",
        )

        data = json.loads(req_reply.content().data())
        for i in range(0, len(data["endpoints"])):
            if data["endpoints"][i]["endpoint"]["type"] == data_type:
                data = data["endpoints"][i]["endpoint"]["_id"]

        if len(data) == 0:
            raise UnavailableEndpointException(
                f"Error while endpoint publication is empty : {data}"
            )
        return data
