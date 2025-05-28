import json
from dataclasses import dataclass
from enum import Enum

from qgis.PyQt.QtCore import QByteArray, QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    CreateProcessingException,
    LaunchExecutionException,
    UnavailableExecutionException,
    UnavailableProcessingException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


class ExecutionStatus(Enum):
    CREATED = "CREATED"
    WAITING = "WAITING"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ABORTED = "ABORTED"


@dataclass
class Execution:
    _id: str
    status: str
    name: str
    creation: str
    parameters: dict
    inputs: dict
    output: dict
    launch: str = ""
    start: str = ""
    finish: str = ""


@dataclass
class Processing:
    name: str
    _id: str


class ProcessingRequestManager:
    def __init__(self):
        """
        Helper for processing request

        """
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore_id: str) -> str:
        """Get base url for processings for a datastore

        :param datastore_id: datastore id
        :type datastore_id: str

        :return: url for processings
        :rtype: str
        """
        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore_id}/processings"

    def get_processing_by_id(
        self, datastore_id: str, possible_ids: list[str]
    ) -> Processing:
        """Get processing from id.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param possible_ids: possible ids for processing
        :type name: list[str]

        :raises UnavailableProcessingException: when error occur during requesting the API

        :return: processing
        :rtype: Processing
        """
        self.log(
            f"{__name__}.get_processing(datastore:{datastore_id},possible_ids:{possible_ids})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableProcessingException(
                f"Error while fetching processing : {err}"
            )

        processing_list = json.loads(reply.data())
        for processing in processing_list:
            if processing["_id"] in possible_ids:
                return Processing(name=processing["name"], _id=processing["_id"])

        raise UnavailableProcessingException(
            f"Processing(s) {possible_ids} not available(s) in server"
        )

    def get_processing(
        self, datastore_id: str, possible_names: list[str]
    ) -> Processing:
        """Get processing from name.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param possible_names: possible names for processing
        :type name: list[str]

        :raises UnavailableProcessingException: when error occur during requesting the API

        :return: processing
        :rtype: Processing
        """
        self.log(
            f"{__name__}.get_processing(datastore:{datastore_id},possible_names:{possible_names})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableProcessingException(
                f"Error while fetching processing : {err}"
            )

        processing_list = json.loads(reply.data())
        for processing in processing_list:
            if processing["name"] in possible_names:
                return Processing(name=processing["name"], _id=processing["_id"])

        raise UnavailableProcessingException(
            f"Processing(s) {possible_names} not available(s) in server"
        )

    def create_processing_execution(self, datastore_id: str, input_map: dict) -> dict:
        """Create a processing execution from an input map

        :param datastore_id: datastore id
        :type datastore_id: str
        :param input_map: input map containing processing id
        :type input_map: dict

        :raises CreateProcessingException: when error occur during requesting the API

        :return: result map containing created execution in _id
        :rtype: dict
        """
        self.log(
            f"{__name__}.create_processing_execution(datastore:{datastore_id},input_map:{input_map})"
        )

        try:
            # encode data
            data = QByteArray()
            data.append(json.dumps(input_map))

            reply = self.request_manager.post_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/executions"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise CreateProcessingException(
                f"Error while creating processing execution : {err}"
            )

        res = json.loads(reply.data())
        return res

    def launch_execution(self, datastore_id: str, exec_id: str) -> None:
        """Launch execution

        :param datastore_id: datastore id
        :type datastore_id: str
        :param exec_id: execution id
        :type exec_id: str

        :raises LaunchExecutionException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.launch_execution(datastore:{datastore_id},exec_id:{exec_id})"
        )

        try:
            self.request_manager.post_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}/executions/{exec_id}/launch"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                data=QByteArray(),
            )
        except ConnectionError as err:
            raise LaunchExecutionException(f"Error while launching executions : {err}")

    def get_execution(self, datastore_id: str, exec_id: str) -> Execution:
        """Get execution.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param exec_id: execution id
        :type exec_id: str

        :raises UnavailableExecutionException: when error occur during requesting the API

        :return: Execution if execution available
        :rtype: Execution
        """
        self.log(
            f"{__name__}.get_execution(datastore:{datastore_id},exec_id:{exec_id})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/executions/{exec_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableExecutionException(
                f"Error while fetching executions : {err}"
            )

        data = json.loads(reply.data())
        execution = self._execution_from_json(data)
        return execution

    def get_stored_data_executions(
        self, datastore_id: str, stored_data_id: str
    ) -> list[Execution]:
        """Get executions list for a stored data.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param stored_data_id: stored_data id
        :type stored_data_id: str

        :raises UnavailableExecutionException: when error occur during requesting the API

        :return: List of execution if stored data available
        :rtype: list[Execution]
        """
        self.log(
            f"{__name__}.get_stored_data_executions(datastore:{datastore_id},stored_data:{stored_data_id})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}/executions?output_stored_data={stored_data_id}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
            data = json.loads(reply.data())
            execution_list = [self.get_execution(datastore_id, e["_id"]) for e in data]
            return execution_list
        except ConnectionError as err:
            raise UnavailableExecutionException(
                f"Error while fetching executions : {err}"
            )

    @staticmethod
    def _execution_from_json(data) -> Execution:
        execution = Execution(
            _id=data["_id"],
            status=data["status"],
            name=data["processing"]["name"],
            creation=data["creation"],
            parameters=data["parameters"],
            inputs=data["inputs"],
            output=data["output"],
        )
        if "launch" in data:
            execution.launch = data["launch"]
        if "start" in data:
            execution.start = data["start"]
        if "finish" in data:
            execution.finish = data["finish"]
        return execution

    def get_execution_logs(self, datastore_id: str, exec_id: str) -> str:
        """Get execution logs.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param exec_id: execution id
        :type exec_id: str

        :raises UnavailableExecutionException: when error occur during requesting the API

        :return: Execution logs if execution available
        :rtype: str
        """
        self.log(
            f"{__name__}.get_execution_logs(datastore:{datastore_id},exec_id:{exec_id})"
        )

        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}/executions/{exec_id}/logs"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return reply.data().decode("utf-8")
        except ConnectionError as err:
            raise UnavailableExecutionException(
                f"Error while fetching execution logs : {err}"
            )
