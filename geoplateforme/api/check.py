import json
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum

from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from geoplateforme.api.custom_exceptions import (
    ReadExecutionLogsException,
    UnavailableExecutionException,
)
from geoplateforme.api.utils import qgs_blocking_get_request
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager

logger = logging.getLogger(__name__)


@dataclass
class CheckExecution:
    id: str
    status: str
    name: str
    creation: str
    start: str = ""
    finish: str = ""


class CheckExecutionStatus(Enum):
    WAITING = "WAITING"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


@dataclass
class Check:
    id: str
    name: str


class CheckRequestManager:
    MAX_LIMIT: int = 50

    def __init__(self):
        """
        Helper for checks request

        """
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.ntwk_requester_blk = QgsBlockingNetworkRequest()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore: str) -> str:
        """
        Get base url for checks for a datastore

        Args:
            datastore: (str) datastore id

        Returns: url for uploads

        """
        return (
            f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/checks"
        )

    def get_execution(self, datastore: str, exec_id: str) -> CheckExecution:
        """
        Get execution.

        Args:
            datastore: (str) datastore id
            exec_id: (str) execution id

        Returns: CheckExecution execution if execution available, raise UnavailableExecutionException otherwise
        """
        self.log(f"{__name__}.get_execution(datastore:{datastore}, exec_id: {exec_id})")

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}/executions/{exec_id}")
        )

        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk, req, UnavailableExecutionException
        )
        data = json.loads(req_reply.content().data().decode("utf-8"))
        execution = CheckExecution(
            id=data["_id"],
            status=data["status"],
            name=data["check"]["name"],
            creation=data["creation"],
        )

        if "start" in data:
            execution.start = data["start"]
        if "finish" in data:
            execution.finish = data["finish"]

        return execution

    def get_execution_logs(self, datastore_id: str, exec_id: str) -> str:
        """
        Get execution logs.

        Args:
            datastore: (str) datastore id
            exec_id: (str) execution id

        Returns: (str) Execution logs if execution available, raise UnavailableExecutionException otherwise
        """
        self.log(
            f"{__name__}.get_execution_logs(datastore:{datastore_id}, exec_id: {exec_id})"
        )

        nb_value = self._get_nb_available_logs(datastore_id, exec_id)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = ""
        for page in range(0, nb_request):
            result += self._get_execution_logs(
                datastore_id, exec_id, page + 1, self.MAX_LIMIT
            )
        return result

    def _get_execution_logs(
        self,
        datastore_id: str,
        exec_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
    ) -> str:
        """Get list of upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param exec_id: execution id
        :type exec_id: str
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int

        :raises ReadExecutionLogsException: when error occur during requesting the API

        :return: logs
        :rtype: str
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}/executions/{exec_id}/logs?page={page}&limit={limit}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadExecutionLogsException(f"Error while fetching upload : {err}")

        data = reply.data().decode("utf-8")

        return data

    def _get_nb_available_logs(self, datastore_id: str, exec_id: str) -> int:
        """Get number of available upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param exec_id: execution id
        :type exec_id: str

        :raises ReadExecutionLogsException: when error occur during requesting the API

        :return: number of available logs
        :rtype: int
        """
        # For now read with maximum limit possible
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}/executions/{exec_id}/logs?limit=1"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadExecutionLogsException(f"Error while fetching upload: {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadExecutionLogsException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val
