#! python3  # noqa: E265

"""
Perform network request.
"""

# ############################################################################
# ########## Imports ###############
# ##################################

# standard library
import mimetypes
import uuid
from codecs import encode
from pathlib import Path
from socket import AF_INET, SOCK_STREAM
from socket import error as socket_error
from socket import socket
from typing import Optional, Union

# PyQGIS
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsBlockingNetworkRequest,
    QgsFileDownloader,
    QgsNetworkReplyContent,
)
from qgis.PyQt.QtCore import (
    QByteArray,
    QCoreApplication,
    QEventLoop,
    QFile,
    QFileInfo,
    QIODevice,
    QUrl,
)
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

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
        http_content_type: str = "application/json",
        http_user_agent: str = f"{__title__}/{__version__}",
    ) -> QNetworkRequest:
        """Build request object using plugin settings.

        :param url: request url, defaults to None
        :type url: QUrl, optional
        :param http_content_type: content type, defaults to "application/json"
        :type http_content_type: str, optional
        :param http_user_agent: http user agent, defaults to f"{__title__}/{__version__}"
        :type http_user_agent: str, optional

        :return: network request object.
        :rtype: QNetworkRequest
        """
        # create network object
        qreq = QNetworkRequest(url=url)

        # headers
        headers = {
            b"Accept": bytes(http_content_type, "utf8"),
            b"User-Agent": bytes(http_user_agent, "utf8"),
        }
        for k, v in headers.items():
            qreq.setRawHeader(k, v)

        return qreq

    def get_url(
        self,
        url: QUrl,
        config_id: Optional[str] = None,
        debug_log_response: bool = True,
        return_req_reply=False,
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

        :raises ConnectionError: if any problem occurs during feed fetching.
        :raises TypeError: if response mime-type is not valid

        :return: feed response in bytes
        :rtype: QByteArray
        """

        auth_manager = QgsApplication.authManager()
        req = QNetworkRequest(url)
        auth_manager.updateNetworkRequest(req, config_id)

        # send request
        try:
            req_status = self.ntwk_requester.get(
                request=req,
                forceRefresh=True,
            )

            # check if request is fine
            if req_status != QgsBlockingNetworkRequest.ErrorCode.NoError:
                self.log(
                    message=self.ntwk_requester.errorMessage(),
                    log_level=Qgis.MessageLevel.Critical,
                    push=True,
                )
                raise ConnectionError(self.ntwk_requester.errorMessage())

            req_reply = self.ntwk_requester.reply()

            if req_reply.error() != QNetworkReply.NetworkError.NoError:
                self.log(
                    message=req_reply.errorString(),
                    log_level=Qgis.MessageLevel.Critical,
                    push=1,
                )
                raise ConnectionError(req_reply.errorString())

            if PlgOptionsManager.get_plg_settings().debug_mode:
                if debug_log_response:
                    self.log(
                        message="GET response: {} ({})".format(
                            req_reply.content().data().decode("utf-8"),
                            convert_octets(req_reply.content().size()),
                        ),
                        log_level=Qgis.MessageLevel.NoLevel,
                        push=False,
                    )
                else:
                    self.log(
                        message="GET response from {}. Received content size: {}".format(
                            url.toString(), convert_octets(req_reply.content().size())
                        ),
                        log_level=Qgis.MessageLevel.NoLevel,
                        push=False,
                    )
            if return_req_reply:
                return req_reply
            return req_reply.content()

        except Exception as err:
            err_msg = self.tr(
                "GET request on URL {} (with auth config {}) failed. Trace: {}".format(
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
        content_type_header: str = "",
        debug_log_response: bool = True,
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
        :param content_type_header: content type header for request, defaults to ""
        :type content_type_header: str, optional
        :param debug_log_response: option to do not log decoded content in debug mode, defaults to True
        :type debug_log_response: bool, optional

        :return: feed response in bytes
        :rtype: QByteArray
        """
        auth_manager = QgsApplication.authManager()
        req = QNetworkRequest(url)
        if content_type_header:
            req.setHeader(
                QNetworkRequest.KnownHeaders.ContentTypeHeader, content_type_header
            )
        auth_manager.updateNetworkRequest(req, config_id)

        # send request
        try:
            req_status = self.ntwk_requester.post(request=req, data=data)

            # check if request is fine
            if req_status != QgsBlockingNetworkRequest.ErrorCode.NoError:
                self.log(
                    message=self.ntwk_requester.errorMessage(),
                    log_level=Qgis.MessageLevel.Critical,
                    push=True,
                )
                raise ConnectionError(self.ntwk_requester.errorMessage())

            req_reply = self.ntwk_requester.reply()

            if req_reply.error() != QNetworkReply.NetworkError.NoError:
                self.log(
                    message=req_reply.errorString(),
                    log_level=Qgis.MessageLevel.Critical,
                    push=True,
                )
                raise ConnectionError(req_reply.errorString())

            if PlgOptionsManager.get_plg_settings().debug_mode:
                if debug_log_response:
                    self.log(
                        message="POST response: {} ({})".format(
                            req_reply.content().data().decode("utf-8"),
                            convert_octets(req_reply.content().size()),
                        ),
                        log_level=Qgis.MessageLevel.NoLevel,
                        push=False,
                    )
                else:
                    self.log(
                        message="POST response from {}. Received content size: {}".format(
                            url.toString(), convert_octets(req_reply.content().size())
                        ),
                        log_level=Qgis.MessageLevel.NoLevel,
                        push=False,
                    )

            return req_reply.content()

        except Exception as err:
            err_msg = self.tr(
                "POST request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )
            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=True)

    def put_url(
        self,
        url: QUrl,
        data: Optional[QByteArray] = None,
        config_id: Optional[str] = None,
        content_type_header: str = "",
        debug_log_response: bool = True,
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

        :return: feed response in bytes
        :rtype: QByteArray
        """
        auth_manager = QgsApplication.authManager()
        req = QNetworkRequest(url)
        if content_type_header:
            req.setHeader(
                QNetworkRequest.KnownHeaders.ContentTypeHeader, content_type_header
            )
        auth_manager.updateNetworkRequest(req, config_id)

        # send request
        try:
            req_status = self.ntwk_requester.put(request=req, data=data)

            # check if request is fine
            if req_status != QgsBlockingNetworkRequest.ErrorCode.NoError:
                self.log(
                    message=self.ntwk_requester.errorMessage(),
                    log_level=Qgis.MessageLevel.Critical,
                    push=True,
                )
                raise ConnectionError(self.ntwk_requester.errorMessage())

            req_reply = self.ntwk_requester.reply()

            if req_reply.error() != QNetworkReply.NetworkError.NoError:
                self.log(
                    message=req_reply.errorString(),
                    log_level=Qgis.MessageLevel.Critical,
                    push=True,
                )
                raise ConnectionError(req_reply.errorString())

            if PlgOptionsManager.get_plg_settings().debug_mode:
                if debug_log_response:
                    self.log(
                        message="PUT response: {} ({})".format(
                            req_reply.content().data().decode("utf-8"),
                            convert_octets(req_reply.content().size()),
                        ),
                        log_level=Qgis.MessageLevel.NoLevel,
                        push=False,
                    )
                else:
                    self.log(
                        message="PUT response from {}. Received content size: {}".format(
                            url.toString(), convert_octets(req_reply.content().size())
                        ),
                        log_level=Qgis.MessageLevel.NoLevel,
                        push=False,
                    )

            return req_reply.content()

        except Exception as err:
            err_msg = self.tr(
                "PUT request on URL {} (with auth config {}) failed. Trace: {}".format(
                    url, config_id, err
                )
            )
            self.log(message=err_msg, log_level=Qgis.MessageLevel.Critical, push=True)

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
        file_downloader.startDownload()
        loop.exec()

        self.log(
            message=f"Download of {remote_url} to {local_path} succeedeed",
            log_level=Qgis.MessageLevel.Success,
        )
        return local_path

    def post_file(
        self,
        url: QUrl,
        file_path: Path,
        config_id: Optional[str] = None,
    ) -> Optional[QByteArray]:
        """Post a file using multipart/form-data

        :param url: url
        :type url: QUrl
        :param file_path: file path to file to upload
        :type file_path: Path
        :param config_id: authentication configuration ID, defaults to None
        :type config_id: Optional[str], optional
        :return: feed response in bytes
        :rtype: Optional[QByteArray]
        """

        fp = QFile(str(file_path))
        fp.open(QIODevice.OpenModeFlag.ReadOnly)

        boundary = f"----OslandiaQGISPluginBoundary{uuid.uuid4().hex}"

        body_list = []

        # Define part for file
        # Add boundary
        body_list.append(encode("--" + boundary))
        body_list.append(
            encode(
                f'Content-Disposition: form-data; name="file"; filename="{QFileInfo(fp).fileName()}"'
            )
        )
        # Define content-type
        file_type = (
            mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        )
        body_list.append(encode(f"Content-Type: {file_type}"))

        # Add file content
        body_list.append(encode(""))
        body_list.append(fp.readAll())

        # Close part for file
        body_list.append(encode("--" + boundary + "--"))

        # Create body for encoded data
        body = b"\r\n".join(body_list)

        # Define content header with multipart/form-data and used boundary
        content_type_header = f"multipart/form-data; boundary={boundary}"

        req_reply = self.post_url(
            url=url,
            data=body,
            config_id=config_id,
            content_type_header=content_type_header,
        )
        return req_reply
