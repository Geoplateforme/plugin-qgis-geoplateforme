import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from geotuileur.toolbelt import PlgLogger, PlgOptionsManager


class StoredDataStatus(Enum):
    CREATED = "CREATED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    UNSTABLE = "UNSTABLE"
    MODIFYING = "MODIFYING"
    DELETED = "DELETED"


@dataclass
class TableRelation:
    name: str
    attributes: {}
    primary_key: str


@dataclass
class StoredData:
    id: str
    name: str
    type: str
    status: str
    tags: dict = None
    type_infos: dict = None

    def get_tables(self) -> List[TableRelation]:
        tables = []
        if self.type_infos:
            tables = [
                TableRelation(
                    relation["name"], relation["attributes"], relation["primary_key"]
                )
                for relation in self.type_infos["relations"]
                if relation["type"] == "TABLE"
            ]
        return tables

    def zoom_levels(self) -> List:
        zoom_levels = []
        if self.type_infos["levels"]:
            zoom_levels = self.type_infos["levels"]
        return zoom_levels


class StoredDataRequestManager:
    class ReadStoredDataException(Exception):
        pass

    class UnavailableStoredData(Exception):
        pass

    class AddTagException(Exception):
        pass

    MAX_LIMIT = 50

    def get_base_url(self, datastore: str) -> str:
        """
        Get base url for stored data for a datastore

        Args:
            datastore: (str) datastore id

        Returns: url for uploads

        """
        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/stored_data"

    def __init__(self):
        """
        Helper for stored_data request

        """
        self.log = PlgLogger().log
        self.ntwk_requester_blk = QgsBlockingNetworkRequest()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_stored_data_list(self, datastore: str) -> List[StoredData]:
        """
        Get list of stored data

        Args:
            datastore: (str) datastore id

        Returns: list of available stored data, raise ReadStoredDataException otherwise
        """
        nb_value = self._get_nb_available_stored_data(datastore)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_stored_data_list(datastore, page + 1, self.MAX_LIMIT)
        return result

    def _get_stored_data_list(
        self, datastore: str, page: int = 1, limit: int = MAX_LIMIT
    ) -> List[StoredData]:
        """
        Get list of stored data

        Args:
            datastore: (str) datastore id
            page: (int) page number (start at 1)
            limit: (int)

        Returns: list of available stored data, raise ReadStoredDataException otherwise
        """
        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)

        req = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}?page={page}&limit={limit}")
        )

        # headers
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        # send request
        resp = self.ntwk_requester_blk.get(req, forceRefresh=True)

        # check response
        if resp != QgsBlockingNetworkRequest.NoError:
            raise self.ReadStoredDataException(
                f"Error while fetching stored data : {self.ntwk_requester_blk.errorMessage()}"
            )

        # check response
        req_reply = self.ntwk_requester_blk.reply()
        if (
            not req_reply.rawHeader(b"Content-Type")
            == "application/json; charset=utf-8"
        ):
            raise self.ReadStoredDataException(
                "Response mime-type is '{}' not 'application/json; charset=utf-8' as required.".format(
                    req_reply.rawHeader(b"Content-type")
                )
            )
        data = json.loads(req_reply.content().data().decode("utf-8"))
        stored_datas_id = [val["_id"] for val in data]

        return [
            self.get_stored_data(datastore, stored_data)
            for stored_data in stored_datas_id
        ]

    def _get_nb_available_stored_data(self, datastore: str) -> int:
        """
        Get number of available stored data

        Args:
            datastore: (str) datastore id

        Returns: (int) number of available data, raise ReadStoredDataException in case of request error

        """
        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)

        # For now read with maximum limit possible
        req = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}?limit=1"))

        # headers
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        # send request
        resp = self.ntwk_requester_blk.get(req, forceRefresh=True)

        # check response
        if resp != QgsBlockingNetworkRequest.NoError:
            raise self.ReadStoredDataException(
                f"Error while fetching stored data : {self.ntwk_requester_blk.errorMessage()}"
            )

        # check response
        req_reply = self.ntwk_requester_blk.reply()
        if (
            not req_reply.rawHeader(b"Content-Type")
            == "application/json; charset=utf-8"
        ):
            raise self.ReadStoredDataException(
                "Response mime-type is '{}' not 'application/json; charset=utf-8' as required.".format(
                    req_reply.rawHeader(b"Content-type")
                )
            )

        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise self.ReadStoredDataException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def get_stored_data(self, datastore: str, stored_data: str) -> StoredData:
        """
        Get stored data by id

        Args:
            datastore: (str) datastore id
            stored_data: (str) stored dat id

        Returns: stored data, raise ReadStoredDataException otherwise
        """
        data = self.get_stored_data_json(datastore, stored_data)
        result = StoredData(
            id=data["_id"], name=data["name"], type=data["type"], status=data["status"]
        )
        if "tags" in data:
            result.tags = data["tags"]
        if "type_infos" in data:
            result.type_infos = data["type_infos"]
        return result

    def get_stored_data_json(self, datastore: str, stored_data: str) -> dict:
        """
        Get dict values of stored data

        Args:
            datastore: (str) datastore id
            stored_data: (str) stored data id

        Returns: dict values of stored data, raise ReadStoredDataException otherwise
        """
        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}/{stored_data}"))

        # headers
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        # send request
        resp = self.ntwk_requester_blk.get(req, forceRefresh=True)

        # check response
        if resp != QgsBlockingNetworkRequest.NoError:
            raise self.ReadStoredDataException(
                f"Error while fetching stored data : {self.ntwk_requester_blk.errorMessage()}"
            )

        # check response
        req_reply = self.ntwk_requester_blk.reply()
        if (
            not req_reply.rawHeader(b"Content-Type")
            == "application/json; charset=utf-8"
        ):
            raise self.ReadStoredDataException(
                "Response mime-type is '{}' not 'application/json; charset=utf-8' as required.".format(
                    req_reply.rawHeader(b"Content-type")
                )
            )

        return json.loads(req_reply.content().data().decode("utf-8"))

    def add_tags(self, datastore: str, stored_data: str, tags: dict) -> None:
        """
        Add tags to stored data

        Args:
            datastore:  (str) datastore id
            stored_data: (str) stored_data id
            tags: (dict) dictionary of tags
        """
        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req_post = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}/{stored_data}/tags")
        )

        # headers
        req_post.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        # encode data
        data = QByteArray()
        data.append(json.dumps(tags))

        # send request
        resp = self.ntwk_requester_blk.post(req_post, data=data, forceRefresh=True)

        # check response
        if resp != QgsBlockingNetworkRequest.NoError:
            raise self.AddTagException(
                f"Error while adding tag to stored_data : {self.ntwk_requester_blk.errorMessage()}"
            )
