import logging

from qgis.core import QgsBlockingNetworkRequest, QgsNetworkReplyContent
from qgis.PyQt.QtCore import QDateTime, Qt
from qgis.PyQt.QtNetwork import QNetworkRequest

logger = logging.getLogger(__name__)


def qgs_blocking_get_request(
    ntwk_requester_blk: QgsBlockingNetworkRequest,
    req: QNetworkRequest,
    exception_type: type,
    expected_type: str = "application/json",
) -> QgsNetworkReplyContent:
    """
    Send GET request with QgsBlockingNetworkRequest and check for expected type

    Args:
        ntwk_requester_blk: (QgsBlockingNetworkRequest)
        req: (QNetworkRequest)
        exception_type: (type) exception type raised if error
        expected_type: (str) expected content type

    Returns: QgsNetworkReplyContent

    """
    # headers
    req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")

    # send request
    resp = ntwk_requester_blk.get(req, forceRefresh=True)

    # check response
    if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
        raise exception_type(ntwk_requester_blk.errorMessage())

    # check response
    req_reply = ntwk_requester_blk.reply()
    content_type = req_reply.rawHeader(b"Content-Type")
    if not content_type == expected_type:
        raise exception_type(
            f"Response mime-type is '{content_type}' not '{expected_type}' as required."
        )
    return req_reply


def as_localized_datetime(date: str) -> str:
    """Try to convert raw creation date as localized datetime using Qt.

    :return: localized date time (or raw creation string if conversion fails)
    :rtype: str
    """
    try:
        dt = QDateTime.fromString(date, Qt.DateFormat.ISODate)
        return dt.toString(Qt.DefaultLocaleLongDate)
    except Exception as exc:
        logger.error(f"Datetime parseing failded. Trace: {exc}")
        return date


def as_datetime(date: str) -> QDateTime:
    """Try to convert raw creation date as datetime using Qt.

    :return: localized date time (or invalid QDateTime if conversion fails)
    :rtype: QDateTime
    """
    try:
        dt = QDateTime.fromString(date, Qt.DateFormat.ISODate)
        return dt
    except Exception as exc:
        logger.error(f"Datetime parseing failded. Trace: {exc}")
        return QDateTime()
