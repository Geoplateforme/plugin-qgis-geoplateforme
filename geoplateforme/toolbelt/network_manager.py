#! python3  # noqa: E265

"""
Perform network request.
"""

# ############################################################################
# ########## Imports ###############
# ##################################

import json
import mimetypes

# standard library
import os
import uuid
from pathlib import Path
from socket import AF_INET, SOCK_STREAM
from socket import error as socket_error
from socket import socket
from typing import Any, Optional, Union

# PyQGIS
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsBlockingNetworkRequest,
    QgsFileDownloader,
    QgsNetworkAccessManager,
    QgsNetworkReplyContent,
)
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
    QNetworkReply,
    QNetworkRequest,
)

# project
from geoplateforme.__about__ import __title__, __version__
from geoplateforme.toolbelt.file_stats import convert_octets
from geoplateforme.toolbelt.log_handler import PlgLogger
from geoplateforme.toolbelt.preferences import PlgOptionsManager

# ############################################################################
# ########## Classes ###############
# ##################################


class NetworkRequestsManager:
    """Helper on network operations."""

    def __init__(self):
        """Initialization."""
        self.log = PlgLogger().log
        self.ntwk_requester = QgsBlockingNetworkRequest()

    @staticmethod
    def is_port_available(host: str = "127.0.0.1", port: int = 7070) -> bool:
        """Check if a port is already in use.

        :param host: host name or IP, defaults to "127.0.0.1"
        :type host: str, optional
        :param port: port number to check, defaults to 7070
        :type port: int, optional

        :return: True if the port is available
        :rtype: bool
        """
        with socket(AF_INET, SOCK_STREAM) as network_socket:
            try:
                network_socket.bind((host, port))
                return True
            except socket_error as err:
                PlgLogger().log(
                    message="Port {} is already in use on {}. Trace: {}".format(
                        port, host, err
                    ),
                    log_level=Qgis.MessageLevel.Critical,
                    push=False,
                )
                return False

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def build_request(
        self,
        url: Optional[QUrl] = None,
        config_id: Optional[str] = None,
        headers: Optional[dict] = None,
        http_content_type: str = "application/json",
        http_user_agent: str = f"{__title__}/{__version__}",
    ) -> QNetworkRequest:
        """Build request object using plugin settings.

        :param url: request url, defaults to None
        :type url: QUrl, optional
        :param config_id: QGIS auth config ID, defaults to None
        :type config_id: str, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional
        :param http_content_type: content type, defaults to "application/json"
        :type http_content_type: str, optional
        :param http_user_agent: http user agent, defaults to f"{__title__}/{__version__}"
        :type http_user_agent: str, optional

        :return: network request object.
        :rtype: QNetworkRequest
        """
        # create network object
        auth_manager = QgsApplication.authManager()
        qreq = QNetworkRequest(url)
        auth_manager.updateNetworkRequest(qreq, config_id)

        # headers
        all_headers = {
            b"Accept": bytes(http_content_type, "utf8"),
            b"User-Agent": bytes(http_user_agent, "utf8"),
        }
        if headers:
            all_headers.update(headers)
        try:
            for k, v in all_headers.items():
                qreq.setRawHeader(k, v)
        except Exception as err:
            self.log(
                message=self.tr(
                    "Something went wrong during request preparation: {}"
                ).format(err),
                log_level=2,
                push=False,
            )

        return qreq

    def get_error_description_from_reply(
        self, req_reply: QgsNetworkReplyContent
    ) -> str:
        """Define error description from reply.
        Check if `error` and `error_description` are available in request reply content

        :param req_reply: request reply
        :type req_reply: QgsNetworkReplyContent
        :return: error description
        :rtype: str
        """
        content = req_reply.content()
        if content.isNull():
            return req_reply.errorString()

        try:
            raw = content.data().decode("utf-8").strip()
            if not raw:
                return req_reply.errorString()

            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return f"{req_reply.errorString()} (invalid JSON: {e})"

        error = data.get("error", req_reply.errorString())
        error_description = ",".join(data.get("error_description", []))

        return f"{error} : {error_description}"

    def check_request_result(
        self, req_status: QgsBlockingNetworkRequest.ErrorCode
    ) -> QgsNetworkReplyContent:
        """Check request result and content

        :param req_status: request status
        :type req_status: QgsBlockingNetworkRequest.ErrorCode
        :raises ConnectionError: an error occured in request
        :return: request reply content
        :rtype: QgsNetworkReplyContent
        """

        req_reply = self.ntwk_requester.reply()

        # check if request is fine
        if req_status != QgsBlockingNetworkRequest.ErrorCode.NoError:
            error = self.get_error_description_from_reply(req_reply)
            self.log(
                message=error,
                log_level=Qgis.MessageLevel.Critical,
                push=False,
            )
            raise ConnectionError(error)

        # check if reply is fine
        if req_reply.error() != QNetworkReply.NetworkError.NoError:
            error = self.get_error_description_from_reply(req_reply)
            self.log(
                message=error,
                log_level=Qgis.MessageLevel.Critical,
                push=False,
            )
            raise ConnectionError(error)

        return req_reply

    def log_reply(
        self,
        method: str,
        req_reply: QgsNetworkReplyContent,
        url: QUrl,
        debug_log_response: Optional[bool],
    ) -> None:
        """Log reply of request

        :param method: request method (GET / POST / PUT / DELETE)
        :type method: str
        :param req_reply: request reply content
        :type req_reply: QgsNetworkReplyContent
        :param url: url used for request
        :type url: QUrl
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        """
        if debug_log_response:
            self.log(
                message="{} response: {} ({})".format(
                    method,
                    req_reply.content().data().decode("utf-8"),
                    convert_octets(req_reply.content().size()),
                ),
                log_level=Qgis.MessageLevel.NoLevel,
                push=False,
            )
        else:
            self.log(
                message="{} response from {}. Received content size: {}".format(
                    method, url.toString(), convert_octets(req_reply.content().size())
                ),
                log_level=Qgis.MessageLevel.NoLevel,
                push=False,
            )

    def get_url(
        self,
        url: QUrl,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        return_req_reply=False,
        headers: Optional[dict] = None,
    ) -> Union[QByteArray, QgsNetworkReplyContent]:
        """Send a get method.

        :param url: URL to request
        :type url: QUrl
        :param config_id: QGIS auth config ID, defaults to None
        :type config_id: str, optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param return_req_reply: option to return request reply instead of request reply content, defaults to False
        :type return_req_reply: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional

        :raises ConnectionError: if any problem occurs during feed fetching.
        :raises TypeError: if response mime-type is not valid

        :return: feed response in bytes
        :rtype: QByteArray
        """

        req = self.build_request(url=url, config_id=config_id, headers=headers)

        # send request
        try:
            req_status = self.ntwk_requester.get(
                request=req,
                forceRefresh=True,
            )
            req_reply = self.check_request_result(req_status)

            if PlgOptionsManager.get_plg_settings().debug_mode:
                self.log_reply(
                    method="GET",
                    req_reply=req_reply,
                    url=url,
                    debug_log_response=debug_log_response,
                )
            if return_req_reply:
                return req_reply
            return req_reply.content()
        except ConnectionError as err:
            raise err
        except Exception as err:
            err_msg = self.tr(
                "GET request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )

            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=False)
            return QByteArray()

    def delete_url(
        self,
        url: QUrl,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        return_req_reply=False,
        headers: Optional[dict] = None,
    ) -> Union[QByteArray, QgsNetworkReplyContent]:
        """Send a get method.

        :param url: URL to request
        :type url: QUrl
        :param config_id: QGIS auth config ID, defaults to None
        :type config_id: str, optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param return_req_reply: option to return request reply instead of request reply content, defaults to False
        :type return_req_reply: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional

        :raises ConnectionError: if any problem occurs during feed fetching.
        :raises TypeError: if response mime-type is not valid

        :return: feed response in bytes
        :rtype: QByteArray
        """

        req = self.build_request(url=url, config_id=config_id, headers=headers)

        # send request
        try:
            req_status = self.ntwk_requester.deleteResource(request=req)
            req_reply = self.check_request_result(req_status)

            if PlgOptionsManager.get_plg_settings().debug_mode:
                self.log_reply(
                    method="DELETE",
                    req_reply=req_reply,
                    url=url,
                    debug_log_response=debug_log_response,
                )

            if return_req_reply:
                return req_reply
            return req_reply.content()
        except ConnectionError as err:
            raise err
        except Exception as err:
            err_msg = self.tr(
                "DELETE request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )

            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=True)
            return QByteArray()

    def post_url(
        self,
        url: QUrl,
        data: Optional[QByteArray] = None,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        headers: Optional[dict] = None,
    ) -> Optional[QByteArray]:
        """Send a post method with data option.
        :raises ConnectionError: if any problem occurs during feed fetching.
        :raises TypeError: if response mime-type is not valid

        :param url: url
        :type url: QUrl
        :param data: data for post, defaults to None
        :type data: QByteArray, optional
        :param config_id: QGIS auth config ID, defaults to None
        :type config_id: str, optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional

        :return: feed response in bytes
        :rtype: QByteArray
        """
        req = self.build_request(url=url, config_id=config_id, headers=headers)

        # send request
        try:
            req_status = self.ntwk_requester.post(request=req, data=data)
            req_reply = self.check_request_result(req_status)

            if PlgOptionsManager.get_plg_settings().debug_mode:
                self.log_reply(
                    method="POST",
                    req_reply=req_reply,
                    url=url,
                    debug_log_response=debug_log_response,
                )

            return req_reply.content()
        except ConnectionError as err:
            raise err
        except Exception as err:
            err_msg = self.tr(
                "POST request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )
            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=False)

    def put_url(
        self,
        url: QUrl,
        data: Optional[QByteArray] = None,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        headers: Optional[dict] = None,
    ) -> Optional[QByteArray]:
        """Send a put method with data option.
        :raises ConnectionError: if any problem occurs during feed fetching.
        :raises TypeError: if response mime-type is not valid

        :param url: url
        :type url: QUrl
        :param data: data for put, defaults to None
        :type data: QByteArray, optional
        :param config_id: QGIS auth config ID, defaults to None
        :type config_id: str, optional
        :param content_type_header: content type header for request, defaults to ""
        :type content_type_header: str, optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional

        :return: feed response in bytes
        :rtype: QByteArray
        """
        req = self.build_request(url=url, config_id=config_id, headers=headers)

        # send request
        try:
            req_status = self.ntwk_requester.put(request=req, data=data)
            req_reply = self.check_request_result(req_status)

            if PlgOptionsManager.get_plg_settings().debug_mode:
                self.log_reply(
                    method="PUT",
                    req_reply=req_reply,
                    url=url,
                    debug_log_response=debug_log_response,
                )

            return req_reply.content()

        except ConnectionError as err:
            raise err
        except Exception as err:
            err_msg = self.tr(
                "PUT request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )
            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=False)

    def download_file_to(
        self,
        remote_url: str,
        local_path: Union[Path, str],
        auth_cfg: Optional[str] = None,
    ) -> str:
        """Download a file from a remote web server accessible through HTTP.

        :param remote_url: remote URL
        :type remote_url: str
        :param local_path: path to the local file
        :type local_path: str
        :param auth_cfg: authentication configuration ID, defaults to None
        :type auth_cfg: Optional[str], optional

        :return: output path
        :rtype: str
        """
        # check if destination path is a str and if parent folder exists
        if isinstance(local_path, Path):
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path = f"{local_path.resolve()}"
        elif isinstance(local_path, str):
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        self.log(
            message=f"Downloading file from {remote_url} to {local_path}",
            log_level=Qgis.MessageLevel.NoLevel,
        )
        # download it
        loop = QEventLoop()
        file_downloader = QgsFileDownloader(
            url=QUrl(remote_url),
            outputFileName=local_path,
            delayStart=True,
            authcfg=auth_cfg,
        )
        file_downloader.downloadExited.connect(loop.quit)

        error_messages: list[str] = []

        def connection_error(errorMessages: list[str]):
            # Need to call function to object error_messages
            # If we do an affectation, python will consider error_messages
            # as a new local variable
            error_messages.extend(errorMessages)

        file_downloader.downloadError.connect(connection_error)

        file_downloader.startDownload()
        loop.exec()

        if error_messages:
            raise ConnectionError(error_messages)
        else:
            self.log(
                message=f"Download of {remote_url} to {local_path} succeedeed",
                log_level=Qgis.MessageLevel.Success,
            )
        return local_path

    @staticmethod
    def add_field(body: QByteArray, boundary: str, name: str, value: str):
        """Add multipart content in a multipart body

        :param body: body to append data
        :type body: QByteArray
        :param boundary: boundary for multipart
        :type boundary: str
        :param name: field name
        :type name: str
        :param value: value
        :type value: str
        """
        body.append(f"--{boundary}\r\n".encode("utf-8"))
        body.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        body.append(f"{value}\r\n".encode("utf-8"))

    @staticmethod
    def add_file_field(
        body: QByteArray,
        boundary: str,
        field_name: str,
        filepath: Path,
        content_type: str,
    ):
        """Add file content to a multipart body

        :param body: body to append data
        :type body: QByteArray
        :param boundary: boundary for multipart
        :type boundary: str
        :param field_name: _description_
        :type field_name: str
        :param filepath: _description_
        :type filepath: Path
        :param content_type: _description_
        :type content_type: str
        """
        with open(filepath, "rb") as f:
            file_content = f.read()
        body.append(f"--{boundary}\r\n".encode("utf-8"))
        body.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filepath.name}"\r\n'.encode(
                "utf-8"
            )
        )
        body.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.append(file_content)
        body.append(b"\r\n")

    def add_value_http_part(
        self, multipart: QHttpMultiPart, name: str, value: str
    ) -> None:
        """Add value in multipart

        :param multipart: multipart
        :type multipart: QHttpMultiPart
        :param name: value name
        :type name: str
        :param value: value
        :type value: str
        """
        val_part = QHttpPart()

        # headers
        val_part.setHeader(
            QNetworkRequest.KnownHeaders.ContentDispositionHeader,
            f'form-data; name="{name}"',
        )
        val_part.setBody(str(value).encode("utf-8"))
        multipart.append(val_part)

    def add_file_part(self, multipart: QHttpMultiPart, file_path: Path) -> None:
        """Add file part in multipart

        :param multipart: multipart
        :type multipart: QHttpMultiPart
        :param file_path: file path
        :type file_path: Path
        """
        file = QFile(str(file_path))
        file.open(QIODevice.OpenModeFlag.ReadOnly)

        # Create filepart
        filepart = QHttpPart()

        file.setParent(
            multipart
        )  # we cannot delete the file now, so delete it with the multiPart

        # headers
        filepart.setHeader(
            QNetworkRequest.KnownHeaders.ContentDispositionHeader,
            f'form-data; name="file"; filename="{os.path.basename(file_path)}"',
        )
        # Define content-type
        file_type = (
            mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        )
        filepart.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader,
            file_type,
        )
        # Define content-length
        filepart.setHeader(
            QNetworkRequest.KnownHeaders.ContentLengthHeader,
            file.size(),
        )

        filepart.setBodyDevice(file)

        multipart.append(filepart)

    def post_file(
        self,
        url: QUrl,
        file_path: Path,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        headers: Optional[dict] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> Optional[QByteArray]:
        """Post a file using multipart/form-data

        :param url: url
        :type url: QUrl
        :param file_path: file path to file to upload
        :type file_path: Path
        :param config_id: authentication configuration ID, defaults to None
        :type config_id: Optional[str], optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional
        :param data: data to add to the request, defaults to None
        :type data: dict[str,Any], optional

        :return: feed response in bytes
        :rtype: Optional[QByteArray]
        """

        self.log(
            f"{__name__}.post_file({url=}, {file_path=}, {config_id=}, {headers=}, {data=})"
        )

        # Create multipart
        multipart = QHttpMultiPart(QHttpMultiPart.ContentType.FormDataType)

        # Add file
        self.add_file_part(multipart=multipart, file_path=file_path)

        # Add data
        if data:
            for key, val in data.items():
                if isinstance(val, list):
                    for value in val:
                        self.add_value_http_part(
                            multipart=multipart, name=key, value=value
                        )
                else:
                    self.add_value_http_part(multipart=multipart, name=key, value=val)

        auth_manager = QgsApplication.authManager()
        req = QNetworkRequest(url)
        auth_manager.updateNetworkRequest(req, config_id)

        # send request
        network_manager = QNetworkAccessManager(self.ntwk_requester)

        reply = network_manager.post(req, multipart)
        multipart.setParent(reply)

        reply.uploadProgress.connect(
            lambda s, t: self.log(self.tr("Uploading {}/{} bytes".format(s, t)))
        )

        # Wait for request finish
        loop = QEventLoop()
        reply.finished.connect(loop.quit)
        loop.exec()

        req_reply = QgsNetworkReplyContent(reply)
        req_reply.setContent(reply.readAll())

        # Check result
        if req_reply.error() != QNetworkReply.NetworkError.NoError:
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            error = self.get_error_description_from_reply(req_reply)
            self.log(
                message=error,
                log_level=Qgis.MessageLevel.Critical,
                push=False,
            )
            if status != 502:
                raise ConnectionError(error)
            else:
                self.log(
                    message=self.tr(
                        "HTTP Code 502 returned but we still consider post file as sucessful because it seems to be related to server side."
                    ),
                    log_level=Qgis.MessageLevel.Warning,
                    push=False,
                )

        if PlgOptionsManager.get_plg_settings().debug_mode:
            self.log_reply(
                method="POST",
                req_reply=req_reply,
                url=url,
                debug_log_response=debug_log_response,
            )
        return req_reply.content()

    def put_file(
        self,
        url: QUrl,
        file_path: Path,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        headers: Optional[dict] = None,
        data: Optional[dict[str, str]] = None,
    ) -> Optional[QByteArray]:
        """Put a file using multipart/form-data

        :param url: url
        :type url: QUrl
        :param file_path: file path to file to upload
        :type file_path: Path
        :param config_id: authentication configuration ID, defaults to None
        :type config_id: Optional[str], optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional
        :param data: data to add to the request, defaults to None
        :type data: dict[str,str], optional

        :return: feed response in bytes
        :rtype: Optional[QByteArray]
        """
        boundary = f"----GeoplateformeQGISPluginBoundary{uuid.uuid4().hex}"

        body = QByteArray()

        if data:
            for key, val in data.items():
                self.add_field(body, boundary, key, val)

        # Define content-type
        file_type = (
            mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        )

        # Add file content
        self.add_file_field(body, boundary, "file", file_path, file_type)

        # Close multipart
        body.append(f"--{boundary}--\r\n".encode("utf-8"))

        # Define content header with multipart/form-data and used boundary
        all_headers = {
            b"Content-Type": bytes(f"multipart/form-data; boundary={boundary}", "utf8"),
        }
        if headers:
            all_headers.update(headers)

        req_reply = self.put_url(
            url=url,
            data=body,
            config_id=config_id,
            debug_log_response=debug_log_response,
            headers=all_headers,
        )
        return req_reply

    def patch_url(
        self,
        url: QUrl,
        data: Optional[QByteArray] = None,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        headers: Optional[dict] = None,
    ) -> Optional[QByteArray]:
        """Send a patch method with data option.
        :raises ConnectionError: if any problem occurs during feed fetching.
        :raises TypeError: if response mime-type is not valid

        :param url: url
        :type url: QUrl
        :param data: data for post, defaults to None
        :type data: QByteArray, optional
        :param config_id: QGIS auth config ID, defaults to None
        :type config_id: str, optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional
        :param headers: headers to add to the request, defaults to None
        :type headers: dict, optional

        :return: feed response in bytes
        :rtype: QByteArray
        """
        req = self.build_request(url=url, config_id=config_id, headers=headers)

        # send request
        try:
            # There is no patch method for QgsBlockingNetworkRequest
            # Need to use QgsNetworkAccessManager to send custom PATCH request
            network_manager = QgsNetworkAccessManager.instance()
            reply = network_manager.sendCustomRequest(req, b"PATCH", data)

            # Wait for result
            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec()

            req_reply = QgsNetworkReplyContent(reply)

            # Check for error
            if reply.error() != QNetworkReply.NetworkError.NoError:
                error = self.get_error_description_from_reply(req_reply)
                self.log(
                    message=error,
                    log_level=Qgis.MessageLevel.Critical,
                    push=False,
                )
                raise ConnectionError(error)

            if PlgOptionsManager.get_plg_settings().debug_mode:
                self.log_reply(
                    method="PATCH",
                    req_reply=req_reply,
                    url=url,
                    debug_log_response=debug_log_response,
                )
            return req_reply.content()

        except ConnectionError as err:
            raise err
        except Exception as err:
            err_msg = self.tr(
                "PATCH request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )
            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=False)

    def test_url(self, url: str, method: str = "head") -> bool:
        """Test if URL is reachable. First, try a HEAD then a GET.

        :param url: URL to test.
        :type url: str
        :param method: _description_, defaults to "head"
        :type method: str, optional

        :return: True if URL is reachable.
        :rtype: bool
        """
        try:
            req = QNetworkRequest(QUrl(url))
            self.ntwk_requester.head(req)
            return True
        except Exception:
            if method == "head":
                return self.test_url(url=url, method="get")
            return False
