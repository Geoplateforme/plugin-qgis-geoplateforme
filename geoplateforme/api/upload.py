import json
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List

# PyQGIS
import requests
from qgis.core import QgsApplication, QgsBlockingNetworkRequest, QgsSettings
from qgis.PyQt.QtCore import (
    QByteArray,
    QCoreApplication,
    QEventLoop,
    QFile,
    QIODevice,
    QUrl,
)
from qgis.PyQt.QtNetwork import (
    QHttpMultiPart,
    QHttpPart,
    QNetworkAccessManager,
    QNetworkRequest,
)

# plugin
from geoplateforme.api.check import CheckExecution, CheckRequestManager
from geoplateforme.api.client import NetworkRequestsManager
from geoplateforme.api.custom_exceptions import (
    DeleteUploadException,
    FileUploadException,
    InvalidToken,
    ReadUploadException,
    UnavailableExecutionException,
    UnavailableUploadException,
    UnavailableUploadFileTreeException,
    UploadClosingException,
    UploadCreationException,
)
from geoplateforme.api.utils import qgs_blocking_get_request
from geoplateforme.toolbelt import PlgLogger, PlgOptionsManager

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


@dataclass
class Upload:
    id: str
    datastore_id: str
    name: str
    description: str
    srs: str
    status: str
    size: int = 0
    tags: dict = None
    last_event: dict = None

    def get_last_event_date(self) -> str:
        result = ""
        if self.last_event and "date" in self.last_event:
            result = self.last_event["date"]
        return result


class UploadRequestManager:
    MAX_LIMIT: int = 50

    def __init__(self):
        """
        Helper for upload request

        """
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.ntwk_requester_blk = QgsBlockingNetworkRequest()
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

    def get_upload_list(self, datastore: str) -> List[Upload]:
        """
        Get list of upload

        Args:
            datastore: (str) datastore id

        Returns: list of available upload, raise ReadUploadException otherwise
        """
        self.log(f"{__name__}.get_upload_list(datastore:{datastore})")
        nb_value = self._get_nb_available_upload(datastore)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_upload_list(datastore, page + 1, self.MAX_LIMIT)
        return result

    def _get_upload_list(
        self, datastore: str, page: int = 1, limit: int = MAX_LIMIT
    ) -> List[Upload]:
        """
        Get list of upload

        Args:
            datastore: (str) datastore id
            page: (int) page number (start at 1)
            limit: (int)

        Returns: list of available upload, raise ReadUploadException otherwise
        """
        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)

        req = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}?page={page}&limit={limit}")
        )

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk, req, ReadUploadException
        )
        data = json.loads(req_reply.content().data().decode("utf-8"))
        uploads_id = [val["_id"] for val in data]

        return [self.get_upload(datastore, upload) for upload in uploads_id]

    def _get_nb_available_upload(self, datastore: str) -> int:
        """
        Get number of available upload

        Args:
            datastore: (str) datastore id

        Returns: (int) number of available data, raise ReadUploadException in case of request error

        """
        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)

        # For now read with maximum limit possible
        req = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}?limit=1"))

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk, req, UnavailableUploadException
        )

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

    def get_upload(self, datastore: str, upload: str) -> Upload:
        """
        Get upload.

        Args:
            datastore: (str) datastore id
            upload: (str) upload id

        Returns: (upload) Upload if available, raise UnavailableUploadException otherwise

        """
        self.log(f"{__name__}.get_upload(datastore:{datastore}, upload: {upload})")

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}/{upload}"))

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk, req, UnavailableUploadException
        )
        data = json.loads(req_reply.content().data().decode("utf-8"))
        return self._upload_from_json(data, datastore)

    def delete(self, datastore: str, upload: str) -> None:
        """
        Delete an upload. Raise DeleteUploadException if an error occurs

        Args:
            datastore: (str) datastore id
            upload: (str) upload id
        """
        self.log(f"{__name__}.delete(datastore:{datastore}, upload: {upload})")

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req_delete = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}/{upload}"))
        # send request
        resp = self.ntwk_requester_blk.deleteResource(req_delete)

        # check response
        if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
            req_reply = self.ntwk_requester_blk.reply()
            data = json.loads(req_reply.content().data().decode("utf-8"))
            raise DeleteUploadException(
                f"Error while deleting upload : {self.ntwk_requester_blk.errorMessage()}. Reply error: {data}"
            )

    @staticmethod
    def _upload_from_json(data, datastore: str) -> Upload:
        upload = Upload(
            id=data["_id"],
            datastore_id=datastore,
            name=data["name"],
            description=data["description"],
            srs=data["srs"],
            status=data["status"],
        )
        if "size" in data:
            upload.size = data["size"]
        if "tags" in data:
            upload.tags = data["tags"]
        if "last_event" in data:
            upload.last_event = data["last_event"]
        return upload

    def get_upload_checks_execution(
        self, datastore: str, upload: str
    ) -> List[CheckExecution]:
        """
        Get upload checks execution.

        Args:
            datastore: (str) datastore id
            upload: (str) upload id

        Returns: [Execution] Upload checks execution list if upload available, raise UnavailableUploadException otherwise
        """
        self.log(
            f"{__name__}.get_upload_checks_execution(datastore:{datastore}, upload: {upload})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}/{upload}/checks"))

        # headers
        req.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        # send request
        resp = self.ntwk_requester_blk.get(req, forceRefresh=True)

        # check response
        if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise UnavailableUploadException(
                f"Error while fetching upload : {self.ntwk_requester_blk.errorMessage()}"
            )

        # check response
        req_reply = self.ntwk_requester_blk.reply()
        data = json.loads(req_reply.content().data())
        exec_list = []

        try:
            check_manager = CheckRequestManager()
            for key, executions in data.items():
                for execution in executions:
                    exec_list.append(
                        check_manager.get_execution(
                            datastore=datastore, exec_id=execution["_id"]
                        )
                    )
        except UnavailableExecutionException as exc:
            raise UnavailableUploadException(
                f"Error while fetching upload check execution : {exc}"
            )
        return exec_list

    def create_upload(
        self,
        datastore: str,
        name: str,
        description: str,
        srs: str,
    ) -> Upload:
        """
        Create upload on Geoplateforme entrepot

        Args:
            datastore: (str) datastore id
            name: (str) upload name
            description: (str) upload description
            srs: (QgsCoordinateReferenceSystem) upload srs

        Returns: Upload if creation succeeded, raise UploadCreationException otherwise

        """
        self.log(
            f"{__name__}.create_upload(datastore:{datastore}, name: {name}, description: {description}, srs: {srs})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req_post = QNetworkRequest(QUrl(self.get_base_url(datastore)))
        # headers
        req_post.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        # encode data
        data = QByteArray()
        data_map = {
            "description": description,
            "name": name,
            "type": "VECTOR",
            "srs": srs,
        }
        data.append(json.dumps(data_map))

        # send request
        resp = self.ntwk_requester_blk.post(req_post, data=data)

        # check response
        if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise UploadCreationException(
                f"Error while creating upload : "
                f"{self.ntwk_requester_blk.errorMessage()}"
            )
        # check response type
        req_reply = self.ntwk_requester_blk.reply()
        data = json.loads(req_reply.content().data())
        return self._upload_from_json(data, datastore)

    @staticmethod
    def get_qgis_proxy_params_str() -> str:
        """Gets the proxy params from QGIS settings.
        Returns None if proxy is not enabled in QGIS. Otherwise,
        returns proxy params in a single string"""
        sett = QgsSettings()
        proxyEnabled = sett.value("proxy/proxyEnabled", "")
        proxyType = sett.value("proxy/proxyType", "")
        proxyHost = sett.value("proxy/proxyHost", "")
        proxyPort = sett.value("proxy/proxyPort", "")
        proxyUser = sett.value("proxy/proxyUser", "")
        proxyPassword = sett.value("proxy/proxyPassword", "")
        if proxyEnabled != "true":
            return ""
        if not proxyHost:
            return ""
        proxyStr = proxyHost + ":" + proxyPort
        if proxyUser:
            proxyStr = proxyUser + ":" + proxyPassword + "@" + proxyStr
        if proxyType == "Socks5Proxy":
            proxyStr = "socks5://" + proxyStr
        else:
            proxyStr = "https://" + proxyStr
        return proxyStr

    def add_file_with_requests(
        self, datastore: str, upload: str, filename: str
    ) -> None:
        """
        Add file to upload by using python package requests

        Args:
            datastore: (str) datastore id
            upload: (str) upload id
            filename: (str) file to import
        """
        self.log(
            f"{__name__}.add_file_with_requests(datastore:{datastore}, upload: {upload}, filename: {filename})"
        )

        # Get api token for requests
        with requests.Session() as session:
            # Add proxy params
            proxy_str = self.get_qgis_proxy_params_str()
            if proxy_str:
                session.proxies = {"http": proxy_str, "https": proxy_str}

            try:
                check = self.request_manager.get_api_token()
                data = json.loads(check.data().decode("utf-8"))
            except InvalidToken as exc:
                self.log(
                    message=self.tr(
                        "Authentication token returned is invalid. Trace: {}".format(
                            exc
                        )
                    ),
                    log_level=2,
                    push=True,
                    duration=0,
                )
                raise FileUploadException(exc)

            session.headers.update({"Authorization": "Bearer " + data["access_token"]})

            # Open file
            with open(filename, "rb") as file:
                if not file:
                    raise FileUploadException(f"Can't open {filename}")

                # Define request param
                files = {"filename": (filename, file)}
                url = f"{self.get_base_url(datastore)}/{upload}/data"
                response = session.post(url, verify=False, timeout=300, files=files)

                # Check response
                if not response.ok:
                    if response.content:
                        error = (
                            f"Error when uploading {filename} to {url}. HTTP error : {response.status_code}.\n"
                            f" Response content : {response.text} "
                        )
                    else:
                        error = f"Error when uploading {filename} to {url}. HTTP error : {response.status_code}."
                    raise FileUploadException(error)

    def add_file(self, datastore: str, upload: str, filename: str) -> None:
        """
        Add file to upload by using QNetworkAccessManager and QHttpMultiPart

        Args:
            datastore: (str) datastore id
            upload: (str) upload id
            filename: (str) file to import
        """
        self.log(
            f"{__name__}.add_file(datastore:{datastore}, upload: {upload}, filename: {filename})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req_post = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}/{upload}/data")
        )

        # Create multipart
        multipart = QHttpMultiPart(QHttpMultiPart.ContentType.FormDataType)
        filepart = QHttpPart()

        # headers
        filepart.setHeader(
            QNetworkRequest.KnownHeaders.ContentDispositionHeader,
            f'form-data; name="filename" filename="{filename}"',
        )

        file = QFile(filename)
        file.setParent(
            multipart
        )  # we cannot delete the file now, so delete it with the multiPart
        file.open(QIODevice.OpenModeFlag.ReadOnly)

        filepart.setBodyDevice(file)
        multipart.append(filepart)

        networkManager = QNetworkAccessManager(self.ntwk_requester_blk)
        QgsApplication.authManager().updateNetworkRequest(
            req_post, self.plg_settings.qgis_auth_id
        )
        reply = networkManager.post(req_post, multipart)
        multipart.setParent(reply)

        # Add event loop to wait for reply execution
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec()

        # check response
        if reply.error() != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise FileUploadException(reply.errorString())

    def close_upload(self, datastore: str, upload: str) -> None:
        """
        Close upload on Geoplateforme entrepot

        Args:
            datastore: (str) datastore id
            upload: (str) upload id
        """
        self.log(f"{__name__}.close_upload(datastore:{datastore}, upload: {upload})")

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req_post = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}/{upload}/close")
        )

        # headers
        req_post.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        # send request
        resp = self.ntwk_requester_blk.post(req_post, data=QByteArray())

        # check response
        if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise UploadClosingException({self.ntwk_requester_blk.errorMessage()})

    def get_upload_file_tree(self, datastore: str, upload: str) -> dict:
        """
        Get upload file tree.

        Args:
            datastore: (str) datastore id
            upload: (str) upload id

        Returns: (dict) Upload file tree if available, raise UnavailableUploadFileTreeException otherwise

        """
        self.log(
            f"{__name__}.get_upload_file_tree(datastore:{datastore}, upload: {upload})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}/{upload}/tree"))

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk, req, UnavailableUploadFileTreeException
        )
        data = json.loads(req_reply.content().data().decode("utf-8"))
        return data
