#! python3

# Standard library
from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

# PyQGIS
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer
from qgis.PyQt.QtCore import QByteArray, QCoreApplication, QUrl

# plugin
from geoplateforme.api.check import CheckExecution, CheckRequestManager
from geoplateforme.api.custom_exceptions import (
    AddTagException,
    DeleteTagException,
    DeleteUploadException,
    FileUploadException,
    ReadUploadException,
    UnavailableExecutionException,
    UnavailableUploadException,
    UnavailableUploadFileTreeException,
    UploadClosingException,
    UploadCreationException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager

logger = logging.getLogger(__name__)


class UploadStatus(Enum):
    CREATED = "CREATED"
    GENERATING = "GENERATING"
    UNSTABLE = "UNSTABLE"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CHECKING = "CHECKING"
    MODIFYING = "MODIFYING"
    DELETED = "DELETED"


class UploadType(Enum):
    VECTOR = "VECTOR"
    RASTER = "RASTER"
    ARCHIVE = "ARCHIVE"
    ROK4PYRAMID = "ROK4-PYRAMID"
    INDEX = "INDEX"
    HISTORICIMAGERY = "HISTORIC-IMAGERY"
    POINTCLOUD = "POINT-CLOUD"
    PYRAMID3D = "PYRAMID-3D"


class UploadVisibility(Enum):
    PRIVATE = "PRIVATE"
    REFERENCED = "REFERENCED"
    PUBLIC = "PUBLIC"


class UploadField(Enum):
    NAME = "name"
    DESCRIPTION = "description"
    TYPE = "type"
    VISIBILITY = "visibility"
    STATUS = "status"
    SRS = "srs"
    CONTACT = "contact"
    SIZE = "size"
    LASTEVENT = "last_event"
    TAGS = "tags"
    BBOX = "bbox"


@dataclass
class Upload:
    _id: str
    datastore_id: str
    is_detailed: bool = False
    # Optional
    _name: Optional[str] = None
    _type: Optional[UploadType] = None
    _visibility: Optional[UploadVisibility] = None
    _description: Optional[str] = None
    _srs: Optional[str] = None
    _status: Optional[UploadStatus] = None
    _contact: Optional[str] = None
    _size: Optional[int] = None
    _tags: Optional[dict] = None
    _extent: Optional[dict] = None
    _type_infos: Optional[dict] = None
    _extra: Optional[dict] = None
    _last_event: Optional[dict] = None

    @property
    def name(self) -> str:
        """Returns the name of the upload.

        :return: upload name
        :rtype: str
        """
        if not self._name and not self.is_detailed:
            self.update_from_api()
        return self._name

    @property
    def type(self) -> UploadType:
        """Returns the type of the upload.

        :return: upload type
        :rtype: UploadType
        """
        if not self._type and not self.is_detailed:
            self.update_from_api()
        return self._type

    @property
    def status(self) -> UploadStatus:
        """Returns the status of the upload.

        :return: upload status
        :rtype: UploadStatus
        """
        if not self._status and not self.is_detailed:
            self.update_from_api()
        return self._status

    @property
    def visibility(self) -> UploadVisibility:
        """Returns the visibility of the upload.

        :return: upload visibility
        :rtype: UploadVisibility
        """
        if not self._visibility and not self.is_detailed:
            self.update_from_api()
        return self._visibility

    @property
    def description(self) -> str:
        """Returns the description of the upload.

        :return: upload description
        :rtype: str
        """
        if not self._description and not self.is_detailed:
            self.update_from_api()
        return self._description

    @property
    def contact(self) -> str:
        """Returns the contact of the upload.

        :return: upload contact
        :rtype: str
        """
        if not self._contact and not self.is_detailed:
            self.update_from_api()
        return self._contact

    @property
    def tags(self) -> dict:
        """Returns the tags of the upload.

        :return: upload tags
        :rtype: dict
        """
        if not self._tags and not self.is_detailed:
            self.update_from_api()
        return self._tags

    @property
    def type_infos(self) -> dict:
        """Returns the type_infos of the upload.

        :return: upload type_infos
        :rtype: dict
        """
        if not self._type_infos and not self.is_detailed:
            self.update_from_api()
        return self._type_infos

    @property
    def extra(self) -> dict:
        """Returns the extra of the upload.

        :return: upload extra
        :rtype: dict
        """
        if not self._extra and not self.is_detailed:
            self.update_from_api()
        return self._extra

    @property
    def size(self) -> int:
        """Returns the size of the upload.

        :return: upload size
        :rtype: int
        """
        if not self._size and not self.is_detailed:
            self.update_from_api()
        return self._size

    @property
    def srs(self) -> str:
        """Returns the srs of the upload.

        :return: upload srs
        :rtype: str
        """
        if not self._srs and not self.is_detailed:
            self.update_from_api()
        return self._srs

    @property
    def extent(self) -> dict:
        """Returns the extent of the upload.

        :return: upload extent
        :rtype: dict
        """
        if not self._extent and not self.is_detailed:
            self.update_from_api()
        return self._extent

    @property
    def last_event(self) -> dict:
        """Returns the last_event of the upload.

        :return: upload last_event
        :rtype: dict
        """
        if not self._last_event and not self.is_detailed:
            self.update_from_api()
        return self._last_event

    def update_from_api(self):
        """Update the upload by calling API details."""
        manager = UploadRequestManager()
        data = manager.get_upload_json(self.datastore_id, self._id)

        if "name" in data:
            self._name = data["name"]
        if "type" in data:
            self._type = UploadType(data["type"])
        if "status" in data:
            self._status = UploadStatus(data["status"])
        if "visibility" in data:
            self._visibility = UploadVisibility(data["visibility"])
        if "description" in data:
            self._description = data["description"]
        if "contact" in data:
            self._contact = data["contact"]
        if "extra" in data:
            self._extra = data["extra"]
        if "tags" in data:
            self._tags = data["tags"]
        if "type_infos" in data:
            self._type_infos = data["type_infos"]
        if "size" in data:
            self._size = data["size"]
        if "srs" in data:
            self._srs = data["srs"]
        if "last_event" in data:
            self._last_event = data["last_event"]
        if "extent" in data:
            self._extent = data["extent"]
        self.is_detailed = True

    def get_last_event_date(self) -> str:
        """Returns the upload last_event date.

        :return: upload last_event date
        :rtype: str
        """
        result = ""
        if self.last_event and "date" in self.last_event:
            result = self.last_event["date"]
        return result

    def create_extent_layer(self) -> QgsVectorLayer:
        """Create extent layer from geojson contains in extent key

        :return: vector layer from stored data extent (invalid layer if extent not defined)
        :rtype: QgsVectorLayer

        """
        if not self.is_detailed:
            self.update_from_api()
        layer = QgsVectorLayer(json.dumps(self.extent), f"{self.name}-extent", "ogr")
        layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        return layer

    @classmethod
    def from_dict(cls, datastore_id: str, val: dict) -> Upload:
        """Load object from a dict.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: Upload
        """
        res = cls(
            _id=val["_id"],
            datastore_id=datastore_id,
        )

        if "name" in val:
            res._name = val["name"]
        if "type" in val:
            res._type = UploadType(val["type"])
        if "status" in val:
            res._status = UploadStatus(val["status"])
        if "visibility" in val:
            res._visibility = UploadVisibility(val["visibility"])
        if "description" in val:
            res._description = val["description"]
        if "contact" in val:
            res._contact = val["contact"]
        if "extra" in val:
            res._extra = val["extra"]
        if "tags" in val:
            res._tags = val["tags"]
        if "type_infos" in val:
            res._type_infos = val["type_infos"]
        if "size" in val:
            res._size = val["size"]
        if "srs" in val:
            res._srs = val["srs"]
        if "last_event" in val:
            res._last_event = val["last_event"]
        if "extent" in val:
            res._extent = val["extent"]

        return res


class UploadRequestManager:
    MAX_LIMIT: int = 50

    def __init__(self):
        """
        Helper for upload request

        """
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def get_base_url(self, datastore: str) -> str:
        """
        Get base url for uploads for a datastore

        Args:
            datastore: (str) datastore id

        Returns: url for uploads

        """
        return (
            f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/uploads"
        )

    def get_upload_list(
        self,
        datastore_id: str,
        with_fields: Optional[List[UploadField]] = None,
        tags: Optional[dict] = None,
    ) -> List[Upload]:
        """Get list of upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param with_fields: list of field to be add to the response
        :type with_fields: List[UploadField], optional
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadUploadException: when error occur during requesting the API

        :return: list of available upload
        :rtype: List[Upload]
        """
        self.log(f"{__name__}.get_upload_list(datastore:{datastore_id})")
        nb_value = self._get_nb_available_upload(datastore_id, tags)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_upload_list(
                datastore_id, page + 1, self.MAX_LIMIT, with_fields, tags
            )
        return result

    def _get_upload_list(
        self,
        datastore_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
        with_fields: Optional[List[UploadField]] = None,
        tags: Optional[dict] = None,
    ) -> List[Upload]:
        """Get list of upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int
        :param with_fields: list of field to be add to the response
        :type with_fields: List[UploadField], optional
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadUploadException: when error occur during requesting the API

        :return: list of available upload
        :rtype: List[Upload]
        """

        # request additionnal fields
        add_fields = ""
        if with_fields:
            for field in with_fields:
                add_fields += f"&fields={field.value}"
        # Add filter on tags
        tags_url = ""
        if tags:
            for key, value in dict.items(tags):
                tags_url += f"&tags[{key}]={value}"

        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}?page={page}&limit={limit}{add_fields}{tags_url}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadUploadException(f"Error while fetching upload : {err}")

        data = json.loads(reply.data())

        return [Upload.from_dict(datastore_id, upload) for upload in data]

    def _get_nb_available_upload(
        self, datastore_id: str, tags: Optional[dict] = None
    ) -> int:
        """Get number of available upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadUploadException: when error occur during requesting the API

        :return: number of available data
        :rtype: int
        """
        # For now read with maximum limit possible
        tags_url = ""
        if tags:
            for key, value in dict.items(tags):
                tags_url += f"&tags[{key}]={value}"
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}?limit=1{tags_url}"),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadUploadException(f"Error while fetching upload: {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadUploadException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def get_upload(self, datastore_id: str, upload_id: str) -> Upload:
        """Get upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str

        :raises UnavailableUploadException: when error occur during requesting the API

        :return: Upload if available
        :rtype: Upload
        """
        self.log(
            f"{__name__}.get_upload(datastore:{datastore_id}, upload: {upload_id})"
        )

        return Upload.from_dict(
            datastore_id, self.get_upload_json(datastore_id, upload_id)
        )

    def get_upload_json(self, datastore_id: str, upload_id: str) -> dict:
        """Get dict values of upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str

        :raises UnavailableUploadException: when error occur during requesting the API

        :return: dict values of upload
        :rtype: dict
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{upload_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return json.loads(reply.data())
        except ConnectionError as err:
            raise UnavailableUploadException(f"Error while fetching upload : {err}")

    def delete(self, datastore_id: str, upload_id: str) -> None:
        """Delete an upload.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str

        :raises DeleteUploadException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete(datastore:{datastore_id}, upload: {upload_id})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{upload_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteUploadException(f"Error while deleting upload : {err}.")

    def add_tags(self, datastore_id: str, upload_id: str, tags: dict) -> None:
        """Add tags to upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str
        :param tags: dictionary of tags
        :type tags: dict

        :raises AddTagException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.add_tags(datastore:{datastore_id},upload:{upload_id}, tags:{tags})"
        )

        try:
            # encode data
            data = QByteArray()
            data.append(json.dumps(tags).encode("utf-8"))
            self.request_manager.post_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{upload_id}/tags"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise AddTagException(f"Error while adding tag to upload : {err}")

    def delete_tags(self, datastore_id: str, upload_id: str, tags: list[str]) -> None:
        """Delete tags of upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str
        :param tags: list of tags to delete
        :type tags: list[str]

        :raises DeleteTagException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.delete_tags(datastore:{datastore_id},upload:{upload_id}, tags:{tags})"
        )

        url = f"{self.get_base_url(datastore_id)}/{upload_id}/tags?"
        # Add all tag to remove
        for tag in tags:
            url += f"&tags={tag}"

        try:
            self.request_manager.delete_url(
                url=QUrl(url),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteTagException(f"Error while deleting tags for upload : {err}")

    def get_upload_checks_execution(
        self, datastore_id: str, upload_id: str
    ) -> List[CheckExecution]:
        """Get upload checks execution.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str

        :raises UnavailableUploadException: when error occur during requesting the API

        :return: Upload checks execution list if upload available
        :rtype: List[CheckExecution]
        """
        self.log(
            f"{__name__}.get_upload_checks_execution(datastore:{datastore_id}, upload: {upload_id})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{upload_id}/checks"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableUploadException(f"Error while fetching upload : {err}")

        # check response
        data = json.loads(reply.data())
        exec_list = []

        try:
            check_manager = CheckRequestManager()
            for key, executions in data.items():
                for execution in executions:
                    exec_list.append(
                        check_manager.get_execution(
                            datastore=datastore_id, exec_id=execution["_id"]
                        )
                    )
        except UnavailableExecutionException as exc:
            raise UnavailableUploadException(
                f"Error while fetching upload check execution : {exc}"
            )
        return exec_list

    def create_upload(
        self,
        datastore_id: str,
        name: str,
        description: str,
        srs: str,
    ) -> Upload:
        """Create upload on Geoplateforme entrepot

        :param datastore_id: datastore id
        :type datastore_id: str
        :param name: upload name
        :type name: str
        :param description: upload description
        :type description: str
        :param srs: upload srs
        :type srs: str

        :raises UploadCreationException: when error occur during requesting the API

        :return: Upload if creation succeeded
        :rtype: Upload
        """
        self.log(
            f"{__name__}.create_upload(datastore:{datastore_id}, name: {name}, description: {description}, srs: {srs})"
        )

        try:
            # encode data
            data = QByteArray()
            data_map = {
                "description": description,
                "name": name,
                "type": "VECTOR",
                "srs": srs,
            }
            data.append(json.dumps(data_map).encode("utf-8"))
            reply = self.request_manager.post_url(
                url=QUrl(self.get_base_url(datastore_id)),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise UploadCreationException(f"Error while creating upload : {err}")

        # check response type
        data = json.loads(reply.data())
        return Upload.from_dict(datastore_id, data)

    def add_file(self, datastore_id: str, upload_id: str, filename: Path) -> None:
        """Add file to upload by using QNetworkAccessManager and QHttpMultiPart

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str
        :param filename: file to import
        :type filename: Path

        :raises FileUploadException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.add_file(datastore:{datastore_id}, upload: {upload_id}, filename: {filename})"
        )

        try:
            self.request_manager.post_file(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}/{upload_id}/data?path={filename.name}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                file_path=filename,
            )
        except ConnectionError as err:
            raise FileUploadException(f"Error while posting upload file : {err}")

    def close_upload(self, datastore_id: str, upload_id: str) -> None:
        """Close upload on Geoplateforme entrepot

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str

        :raises UploadClosingException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.close_upload(datastore:{datastore_id}, upload: {upload_id})"
        )

        try:
            # encode data
            data = QByteArray()
            self.request_manager.post_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{upload_id}/close"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise UploadClosingException(f"Error while closing upload : {err}")

    def get_upload_file_tree(self, datastore_id: str, upload_id: str) -> dict:
        """Get upload file tree.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload name
        :type upload_id: str

        :raises UnavailableUploadFileTreeException: when error occur during requesting the API

        :return: Upload file tree if available
        :rtype: dict
        """
        self.log(
            f"{__name__}.get_upload_file_tree(datastore:{datastore_id}, upload: {upload_id})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{upload_id}/tree"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableUploadFileTreeException(
                f"Error while fetching file tree : {err}"
            )

        data = json.loads(reply.data())
        return data
