# standard
import json
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

# PyQGIS
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from geoplateforme.api.configuration import Configuration, ConfigurationType

# project
from geoplateforme.api.custom_exceptions import (
    OfferingCreationException,
    ReadOfferingException,
    SynchronizeOfferingException,
    UnavailableOfferingsException,
)
from geoplateforme.api.utils import qgs_blocking_get_request
from geoplateforme.toolbelt.log_handler import PlgLogger
from geoplateforme.toolbelt.network_manager import NetworkRequestsManager
from geoplateforme.toolbelt.preferences import PlgOptionsManager

logger = logging.getLogger(__name__)


class OfferingField(Enum):
    OPEN = "open"
    AVAILABLE = "available"
    LAYER_NAME = "layer_name"
    TYPE = "type"
    STATUS = "status"
    ENDPOINT = "endpoint"
    CONFIGURATION = "configuration"
    URLS = "urls"
    EXTRA = "extra"


class OfferingStatus(Enum):
    PUBLISHING = "PUBLISHING"
    MODIFYING = "MODIFYING"
    PUBLISHED = "PUBLISHED"
    UNPUBLISHING = "UNPUBLISHING"
    UNSTABLE = "UNSTABLE"


@dataclass
class Offering:
    _id: str
    datastore_id: str
    is_detailed: bool = False

    # Optional
    _open: Optional[bool] = None
    _available: Optional[bool] = None
    _layer_name: Optional[str] = None
    _type: Optional[ConfigurationType] = None
    _status: Optional[OfferingStatus] = None
    _configuration: Optional[Configuration] = None
    _endpoint: Optional[dict] = None
    _urls: Optional[List[dict]] = None
    _extra: Optional[dict] = None

    @property
    def open(self) -> bool:
        """Returns True if the offering is open False otherwise.

        :return: offering is open
        :rtype: bool
        """
        if not self._open and not self.is_detailed:
            self.update_from_api()
        return self._open

    @property
    def available(self) -> bool:
        """Returns True if the offering is available False otherwise.

        :return: offering is available
        :rtype: bool
        """
        if not self._available and not self.is_detailed:
            self.update_from_api()
        return self._available

    @property
    def layer_name(self) -> str:
        """Returns the name of the offering.

        :return: offering name
        :rtype: str
        """
        if not self._layer_name and not self.is_detailed:
            self.update_from_api()
        return self._layer_name

    @property
    def type(self) -> ConfigurationType:
        """Returns the type of the offering.

        :return: offering type
        :rtype: ConfigurationType
        """
        if not self._type and not self.is_detailed:
            self.update_from_api()
        return self._type

    @property
    def status(self) -> OfferingStatus:
        """Returns the status of the offering.

        :return: offering status
        :rtype: OfferingStatus
        """
        if not self._status and not self.is_detailed:
            self.update_from_api()
        return self._status

    @property
    def configuration(self) -> Configuration:
        """Returns the configuration dict for the offering.

        :return: configuration dict
        :rtype: dict
        """
        if not self._configuration and not self.is_detailed:
            self.update_from_api()
        return self._configuration

    @property
    def endpoint(self) -> dict:
        """Returns the endpoint dict for the offering.

        :return: endpoint dict
        :rtype: dict
        """
        if not self._endpoint and not self.is_detailed:
            self.update_from_api()
        return self._endpoint

    @property
    def urls(self) -> List[dict]:
        """Returns the url dict list for the offering.

        :return: url dict list
        :rtype: List[dict]
        """
        if not self._urls and not self.is_detailed:
            self.update_from_api()
        return self._urls

    @property
    def extra(self) -> dict:
        """Returns the extra dict for the offering.

        :return: extra dict
        :rtype: dict
        """
        if not self._extra and not self.is_detailed:
            self.update_from_api()
        return self._extra

    @classmethod
    def from_dict(cls, datastore_id: str, val: dict):
        """Load object from a dict.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: Configuration
        """
        res = cls(
            _id=val["_id"],
            datastore_id=datastore_id,
        )
        if "open" in val:
            res._open = val["open"]
        if "available" in val:
            res._available = val["available"]
        if "layer_name" in val:
            res._layer_name = val["layer_name"]
        if "type" in val:
            res._type = ConfigurationType(val["type"])
        if "status" in val:
            res._status = OfferingStatus(val["status"])
        if "configuration" in val:
            res._configuration = Configuration.from_dict(
                datastore_id=datastore_id, val=val["configuration"]
            )
        if "endpoint" in val:
            res._endpoint = val["endpoint"]
        if "urls" in val:
            res._urls = val["urls"]
        if "extra" in val:
            res._extra = val["extra"]

        return res

    def update_from_api(self):
        """Update the configuration by calling API details."""
        manager = OfferingsRequestManager()
        val = manager.get_offering_json(self.datastore_id, self._id)

        if "open" in val:
            self._open = val["open"]
        if "available" in val:
            self._available = val["available"]
        if "layer_name" in val:
            self._layer_name = val["layer_name"]
        if "type" in val:
            self._type = ConfigurationType(val["type"])
        if "status" in val:
            self._status = OfferingStatus(val["status"])
        if "configuration" in val:
            self._configuration = Configuration.from_dict(
                datastore_id=self.datastore_id, val=val["configuration"]
            )
        if "endpoint" in val:
            self._endpoint = val["endpoint"]
        if "urls" in val:
            self._urls = val["urls"]
        if "extra" in val:
            self._extra = val["extra"]
        self.is_detailed = True


class OfferingsRequestManager:
    MAX_LIMIT = 50

    def __init__(self):
        """
        Helper for get offerings request

        """
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.ntwk_requester_blk = QgsBlockingNetworkRequest()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore: str) -> str:
        """
        Get base url for offerings

        Args:
            datastore: (str)

        Returns: url for offerings
        """
        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/offerings"

    def get_config_base_url(self, datastore: str) -> str:
        """
        Get base url for configurations

        Args:
            datastore: (str)

        Returns: url for configurations
        """
        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/configurations"

    def get_offerings_id(self, datastore: str, stored_data: str) -> list:
        """
        Get offerings id for a specific stored data on Geoplateforme entrepot

        Args:
            datastore id :(str)
            stored data id : (str)

        """
        self.log(
            f"{__name__}.get_offerings_id(datastore:{datastore},stored_data:{stored_data})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req = QNetworkRequest(
            QUrl(f"{self.get_base_url(datastore)}?stored_data={stored_data}")
        )

        # headers
        req_reply = qgs_blocking_get_request(
            self.ntwk_requester_blk, req, UnavailableOfferingsException
        )

        data = json.loads(req_reply.content().data().decode("utf-8"))

        offering_ids = [offering["_id"] for offering in data]

        return offering_ids

    def delete_offering(self, datastore: str, offering_id: str):
        """
        Delete offering

        Args:
            datastore: (str)
            offering_id : (str)
        """
        self.log(
            f"{__name__}.delete_offering(datastore:{datastore},offering_id:{offering_id})"
        )

        self.ntwk_requester_blk.setAuthCfg(self.plg_settings.qgis_auth_id)
        req_get = QNetworkRequest(QUrl(f"{self.get_base_url(datastore)}/{offering_id}"))

        # headers
        req_get.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        # send request
        resp = self.ntwk_requester_blk.deleteResource(req_get)

        # check response
        if resp != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise UnavailableOfferingsException(
                f"Error while fetching processing : {self.ntwk_requester_blk.errorMessage()}"
            )

    def create_offering(
        self, visibility: str, endpoint: str, datastore: str, configuration_id: str
    ) -> Offering:
        """
        Create offering on Geoplateforme entrepot

        Args:
            configuration_id: (str) datastore_id :(str)
            visibility :(str) endpoint : (str)

        """
        self.log(
            f"{__name__}.create_offering(visibility:{visibility}, endpoint: {endpoint}, datastore: {datastore}, configuration_id: {configuration_id})"
        )

        # encode data
        data = QByteArray()
        data_map = {"visibility": visibility, "endpoint": endpoint, "open": True}

        data.append(json.dumps(data_map))

        try:
            # send request
            reply = self.request_manager.post_url(
                url=QUrl(
                    f"{self.get_config_base_url(datastore)}/{configuration_id}/offerings"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )

        except ConnectionError as err:
            raise OfferingCreationException(f"Error while creating publication : {err}")

        data = json.loads(reply.data())
        return Offering.from_dict(datastore_id=datastore, val=data)

    def get_offering_list(
        self,
        datastore_id: str,
        with_fields: Optional[List[OfferingField]] = None,
        configuration_id: Optional[str] = None,
    ) -> List[Offering]:
        """Get list of offering

        :param datastore_id: datastore id
        :type datastore_id: str
        :param with_fields: list of field to be add to the response
        :type with_fields: List[ConfigurationField], optional
        :param configuration_id: configuration id
        :type configuration_id: str, optional

        :raises ReadOfferingException: when error occur during requesting the API

        :return: list of available offering
        :rtype: List[Offering]
        """
        self.log(
            f"{__name__}.get_offering_list(datastore:{datastore_id},configuration_id:{configuration_id})"
        )

        nb_value = self._get_nb_available_offering(datastore_id, configuration_id)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_offering_list(
                datastore_id, page + 1, self.MAX_LIMIT, with_fields, configuration_id
            )
        return result

    def _get_offering_list(
        self,
        datastore_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
        with_fields: Optional[List[OfferingField]] = None,
        configuration_id: Optional[str] = None,
    ) -> List[Offering]:
        """Get list of offering

        :param datastore_id: datastore id
        :type datastore_id: str
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int
        :param with_fields: list of field to be add to the response
        :type with_fields: List[ConfigurationField], optional
        :param configuration_id: configuration id
        :type configuration_id: str, optional

        :raises ReadOfferingException: when error occur during requesting the API

        :return: list of available offering
        :rtype: List[Offering]
        """

        # request additionnal fields
        add_fields = ""
        if with_fields:
            for field in with_fields:
                add_fields += f"&fields={field.value}"
        # Add filter on configuration
        configuration_url = ""
        if configuration_id:
            configuration_url = f"&configuration={configuration_id}"

        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}?page={page}&limit={limit}{add_fields}{configuration_url}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadOfferingException(f"Error while fetching offering : {err}")

        data = json.loads(reply.data())
        return [Offering.from_dict(datastore_id, offering) for offering in data]

    def _get_nb_available_offering(
        self, datastore_id: str, configuration_id: Optional[str] = None
    ) -> int:
        """Get number of available offering

        :param datastore_id: datastore id
        :type datastore_id: str
        :param configuration_id: configuration id
        :type configuration_id: str, optional

        :raises ReadOfferingException: when error occur during requesting the API

        :return: number of available offering
        :rtype: int
        """
        # For now read with maximum limit possible

        # Add filter on configuration
        configuration_url = ""
        if configuration_id:
            configuration_url = f"&configuration={configuration_id}"
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}?limit=1{configuration_url}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadOfferingException(f"Error while fetching offering : {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadOfferingException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def get_offering(self, datastore: str, offering: str) -> Offering:
        """
        Get offering informations

        Args :
            datastore : (str) , offering : (str)
        """
        self.log(
            f"{__name__}.get_offering(datastore:{datastore}, offering: {offering})"
        )

        return Offering.from_dict(
            datastore, self.get_offering_json(datastore, offering)
        )

    def get_offering_json(self, datastore_id: str, offering: str) -> dict:
        """Get dict values of offering

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering: offering id
        :type offering: str

        :raises ReadOfferingException: when error occur during requesting the API

        :return: dict values of stored data
        :rtype: dict
        """
        try:
            # send request
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{offering}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return json.loads(reply.data().decode("utf-8"))
        except ConnectionError as err:
            raise ReadOfferingException(f"Error while getting offering : {err}")

    def synchronize(self, datastore_id: str, offering_id: str) -> None:
        """Synchronize configuration update on service

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering_id: offering id
        :type offering_id: str
        :raises SynchronizeOfferingException: error when synchronizing offering
        """
        try:
            # send request
            self.request_manager.put_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{offering_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise SynchronizeOfferingException(
                f"Error while synchronizing offering : {err}"
            )
