# standard
import json
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

# PyQGIS
from qgis.PyQt.QtCore import QByteArray, QUrl

# project
from geoplateforme.api.custom_exceptions import (
    AddTagException,
    ConfigurationCreationException,
    ReadConfigurationException,
    UnavailableConfigurationException,
    UpdateConfigurationException,
)
from geoplateforme.toolbelt.log_handler import PlgLogger
from geoplateforme.toolbelt.network_manager import NetworkRequestsManager
from geoplateforme.toolbelt.preferences import PlgOptionsManager

logger = logging.getLogger(__name__)


@dataclass
class WmsVectorTableStyle:
    native_name: str
    stl_file: Optional[str] = None
    ftl_file: Optional[str] = None


@dataclass
class WfsRelation:
    native_name: str
    title: str
    abstract: str
    public_name: Optional[str] = None
    keywords: Optional[List[str]] = None


class ConfigurationField(Enum):
    NAME = "name"
    LAYER_NAME = "layer_name"
    TYPE = "type"
    STATUS = "status"
    ATTRIBUTIONS = "attributions"
    METADATAS = "metadatas"
    TAGS = "tags"
    LAST_EVENT = "last_event"


class ConfigurationType(Enum):
    WMS_VECTOR = "WMS-VECTOR"
    WFS = "WFS"
    WMTS_TMS = "WMTS-TMS"
    WMS_RASTER = "WMS-RASTER"
    DOWNLOAD = "DOWNLOAD"
    ITINERARY_ISOCURVE = "ITINERARY-ISOCURVE"
    ALTIMETRY = "ALTIMETRY"
    SEARCH = "SEARCH"
    VECTOR_TMS = "VECTOR-TMS"


class ConfigurationStatus(Enum):
    UNPUBLISHED = "UNPUBLISHED"
    PUBLISHED = "PUBLISHED"
    SYNCHRONIZING = "SYNCHRONIZING"


class ConfigurationMetadataType(Enum):
    ISO19115_2003 = "ISO19115:2003"
    FGDC = "FGDC"
    TC211 = "TC211"
    ISO_19139 = "19139"
    OTHER = "Other"


@dataclass
class ConfigurationMetadata:
    format: str
    url: str
    type: ConfigurationMetadataType


@dataclass
class Configuration:
    _id: str
    datastore_id: str
    is_detailed: bool = False

    # Optional
    _name: Optional[str] = None
    _layer_name: Optional[str] = None
    _type: Optional[ConfigurationType] = None
    _status: Optional[ConfigurationStatus] = None
    _tags: Optional[dict] = None
    _attribution: Optional[dict] = None
    _last_event: Optional[dict] = None
    _extra: Optional[dict] = None
    _metadata: Optional[list[ConfigurationMetadata]] = None
    _type_infos: Optional[dict] = None

    @property
    def name(self) -> str:
        """Returns the name of the configuration.

        :return: configuration name
        :rtype: str
        """
        if not self._name and not self.is_detailed:
            self.update_from_api()
        return self._name

    @property
    def layer_name(self) -> str:
        """Returns the name of the configuration.

        :return: configuration name
        :rtype: str
        """
        if not self._layer_name and not self.is_detailed:
            self.update_from_api()
        return self._layer_name

    @property
    def type(self) -> ConfigurationType:
        """Returns the type of the configuration.

        :return: configuration type
        :rtype: ConfigurationType
        """
        if not self._type and not self.is_detailed:
            self.update_from_api()
        return self._type

    @property
    def status(self) -> ConfigurationStatus:
        """Returns the status of the configuration.

        :return: configuration status
        :rtype: ConfigurationStatus
        """
        if not self._status and not self.is_detailed:
            self.update_from_api()
        return self._status

    @property
    def tags(self) -> dict:
        """Returns the tags of the configuration.

        :return: configuration tags
        :rtype: dict
        """
        if not self._tags and not self.is_detailed:
            self.update_from_api()
        return self._tags

    @property
    def attribution(self) -> dict:
        """Returns the attribution of the configuration.

        :return: configuration attribution
        :rtype: dict
        """
        if not self._attribution and not self.is_detailed:
            self.update_from_api()
        return self._attribution

    @property
    def url_title(self) -> str:
        """Return the url defined in attribution

        :return: attribution title
        :rtype: str
        """
        if self._attribution and "title" in self._attribution:
            return self._attribution["title"]
        else:
            return ""

    @url_title.setter
    def url_title(self, val: str) -> None:
        """Set the title defined in attribution

        :param val: title
        :type val: str
        """
        self._attribution["title"] = val

    @property
    def url(self) -> str:
        """Return the url defined in attribution

        :return: attribution url
        :rtype: str
        """
        if self._attribution and "url" in self._attribution:
            return self._attribution["url"]
        else:
            return ""

    @url.setter
    def url(self, val: str) -> None:
        """Set the url defined in attribution

        :param val: url
        :type val: str
        """
        self._attribution["url"] = val

    @property
    def last_event(self) -> dict:
        """Returns the last_event of configuration.

        :return: configuration last_event
        :rtype: dict
        """
        if not self._last_event and not self.is_detailed:
            self.update_from_api()
        return self._last_event

    def get_last_event_date(self) -> str:
        """Returns the configuration last_event date.

        :return: configuration last_event date
        :rtype: str
        """
        result = ""
        if self._last_event and "date" in self._last_event:
            result = self._last_event["date"]
        return result

    @property
    def extra(self) -> dict:
        """Returns the extra of configuraiton.

        :return: configuration extra
        :rtype: dict
        """
        if not self._extra and not self.is_detailed:
            self.update_from_api()
        return self._extra

    @property
    def metadata(self) -> list[ConfigurationMetadata]:
        """Returns the metadata of the configuration.

        :return: configuration metadata
        :rtype: dict
        """
        if not self._metadata and not self.is_detailed:
            self.update_from_api()
        return self._metadata

    @property
    def type_infos(self) -> dict:
        """Returns the type_infos of the configuration.

        :return: configuration type_infos
        :rtype: dict
        """
        if not self._type_infos and not self.is_detailed:
            self.update_from_api()
        return self._type_infos

    @property
    def title(self) -> str:
        """Get the title for type_infos

        :return: title for type_infos
        :rtype: str
        """
        if self._type_infos and "title" in self._type_infos:
            return self._type_infos["title"]
        else:
            return ""

    @title.setter
    def title(self, val: str) -> None:
        """Set the title in type_infos

        :param val: title
        :type val: str
        """
        self._type_infos["title"] = val

    @property
    def abstract(self) -> str:
        """Get the abstract from type_infos

        :return: abstract from type_infos
        :rtype: str
        """
        if self._type_infos and "abstract" in self._type_infos:
            return self._type_infos["abstract"]
        else:
            return ""

    @abstract.setter
    def abstract(self, val: str) -> None:
        """Set the abstract for type_indos

        :param val: abstract
        :type val: str
        """
        self._type_infos["abstract"] = val

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
        if "name" in val:
            res._name = val["name"]
        if "layer_name" in val:
            res._layer_name = val["layer_name"]
        if "type" in val:
            res._type = ConfigurationType(val["type"])
        if "status" in val:
            res._status = ConfigurationStatus(val["status"])
        if "tags" in val:
            res._tags = val["tags"]
        if "attribution" in val:
            res._attribution = val["attribution"]
        if "last_event" in val:
            res._last_event = val["last_event"]
        if "extra" in val:
            res._extra = val["extra"]
        if "metadata" in val:
            res._metadata = []
            for metadata in val["metadata"]:
                res._metadata.append(
                    ConfigurationMetadata(
                        format=metadata["format"],
                        url=metadata["url"],
                        type=ConfigurationMetadataType(metadata["type"]),
                    )
                )
        if "type_infos" in val:
            res._type_infos = val["type_infos"]

        return res

    def update_from_api(self):
        """Update the configuration by calling API details."""
        manager = ConfigurationRequestManager()
        data = manager.get_configuration_json(self.datastore_id, self._id)

        if "name" in data:
            self._name = data["name"]
        if "layer_name" in data:
            self._layer_name = data["layer_name"]
        if "type" in data:
            self._type = ConfigurationType(data["type"])
        if "status" in data:
            self._status = ConfigurationStatus(data["status"])
        if "tags" in data:
            self._tags = data["tags"]
        if "attribution" in data:
            self._attribution = data["attribution"]
        if "last_event" in data:
            self._last_event = data["last_event"]
        if "extra" in data:
            self._extra = data["extra"]
        if "metadata" in data:
            self._metadata = []
            for metadata in data["metadata"]:
                self._metadata.append(
                    ConfigurationMetadata(
                        format=metadata["format"],
                        url=metadata["url"],
                        type=ConfigurationMetadataType(metadata["type"]),
                    )
                )
        if "type_infos" in data:
            self._type_infos = data["type_infos"]
        self.is_detailed = True


class ConfigurationRequestManager:
    MAX_LIMIT = 50

    def __init__(self):
        """
        Helper for configuration request

        """
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore: str) -> str:
        """
        Get base url for configuration for a datastore

        Args:
            datastore: (str) datastore id

        Returns: url for configuration

        """
        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/configurations"

    def create_configuration(
        self,
        datastore: str,
        configuration: Configuration,
    ) -> str:
        """
        Create configuration on Geoplateforme entrepot

        Args:
            datastore: (str) datastore id
            configuration

        Returns: Upload if creation succeeded, raise UploadCreationException otherwise

        """
        self.log(
            f"{__name__}.create_configuration(datastore:{datastore},configuration: {configuration})"
        )

        # encode data
        data = QByteArray()
        data_map = {
            "type": configuration.type.value,
            "metadata": [
                {"format": meta.format, "url": meta.url, "type": meta.type.value}
                for meta in configuration.metadata
            ],
            "name": configuration.name,
            "layer_name": configuration.layer_name,
            "type_infos": configuration.type_infos,
        }
        if configuration.attribution:
            data_map["attribution"] = configuration.attribution
        data.append(json.dumps(data_map))
        try:
            # send request
            reply = self.request_manager.post_url(
                url=QUrl(self.get_base_url(datastore)),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise ConfigurationCreationException(
                f"Error while creating configuration : {err}"
            )
        data = json.loads(reply.data())
        return data["_id"]

    def get_configurations_id(self, datastore: str, stored_data: str) -> list:
        """
        get  configuration id list from stored data

        Args:
            datastore: (str) stored_data : (str)
        """
        self.log(
            f"{__name__}.get_configurations_id(datastore:{datastore}, stored_data: {stored_data})"
        )
        try:
            # send request
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore)}?stored_data={stored_data}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise UnavailableConfigurationException(
                f"Error while getting configuration : {err}"
            )
        data = json.loads(reply.data().decode("utf-8"))
        configuration_ids = [configuration["_id"] for configuration in data]

        return configuration_ids

    def get_configuration(self, datastore: str, configuration: str) -> Configuration:
        """
        get configuration informations

        Args :
            datastore : (str) , configuration : (str)
        """
        self.log(
            f"{__name__}.get_configuration(datastore:{datastore}, configuration: {configuration})"
        )

        config = Configuration.from_dict(
            datastore, self.get_configuration_json(datastore, configuration)
        )
        config.is_detailed = True
        return config

    def get_configuration_json(self, datastore_id: str, configuration: str) -> dict:
        """Get dict values of configuration

        :param datastore_id: datastore id
        :type datastore_id: str
        :param configuration: configuration id
        :type configuration: str

        :raises ReadConfigurationException: when error occur during requesting the API

        :return: dict values of stored data
        :rtype: dict
        """
        try:
            # send request
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{configuration}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return json.loads(reply.data().decode("utf-8"))
        except ConnectionError as err:
            raise ReadConfigurationException(
                f"Error while getting configuration : {err}"
            )

    def get_configuration_list(
        self,
        datastore_id: str,
        with_fields: Optional[List[ConfigurationField]] = None,
        tags: Optional[dict] = None,
    ) -> List[Configuration]:
        """Get list of configuration

        :param datastore_id: datastore id
        :type datastore_id: str
        :param with_fields: list of field to be add to the response
        :type with_fields: List[ConfigurationField], optional
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadConfigurationException: when error occur during requesting the API

        :return: list of available configuration
        :rtype: List[Configuration]
        """
        self.log(f"{__name__}.get_configuration_list(datastore:{datastore_id})")

        nb_value = self._get_nb_available_configuration(datastore_id, tags)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_configuration_list(
                datastore_id, page + 1, self.MAX_LIMIT, with_fields, tags
            )
        return result

    def _get_configuration_list(
        self,
        datastore_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
        with_fields: Optional[List[ConfigurationField]] = None,
        tags: Optional[dict] = None,
    ) -> List[Configuration]:
        """Get list of configuration

        :param datastore_id: datastore id
        :type datastore_id: str
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int
        :param with_fields: list of field to be add to the response
        :type with_fields: List[ConfigurationField], optional
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadConfigurationException: when error occur during requesting the API

        :return: list of available configuration
        :rtype: List[Configuration]
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
            raise ReadConfigurationException(
                f"Error while fetching configuration : {err}"
            )

        data = json.loads(reply.data())
        return [
            Configuration.from_dict(datastore_id, stored_data) for stored_data in data
        ]

    def _get_nb_available_configuration(
        self, datastore_id: str, tags: Optional[dict] = None
    ) -> int:
        """Get number of available configuration

        :param datastore_id: datastore id
        :type datastore_id: str
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadConfigurationException: when error occur during requesting the API

        :return: number of available configuration
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
            raise ReadConfigurationException(
                f"Error while fetching configuration : {err}"
            )

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadConfigurationException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def delete_configuration(self, datastore: str, configuration_id: str):
        """
        Delete a configuration

        Args:
            configuration_id: (str) datastore_id : (str)
        """
        self.log(
            f"{__name__}.delete_configuration(datastore:{datastore}, configuration_id: {configuration_id})"
        )

        try:
            # send request
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url(datastore)}/{configuration_id}"),
                config_id=self.plg_settings.qgis_auth_id,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )

        except ConnectionError as err:
            raise UnavailableConfigurationException(
                f"Error while getting configuration : {err}"
            )

    def add_tags(self, datastore_id: str, configuration_id: str, tags: dict) -> None:
        """Add tags to stored data

        :param datastore_id: datastore id
        :type datastore_id: str
        :param configuration_id: configuration id
        :type configuration_id: str
        :param tags: dictionary of tags
        :type tags: dict

        :raises AddTagException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.add_tags(datastore_id:{datastore_id},configuration_id:{configuration_id}, tags:{tags})"
        )

        try:
            # encode data
            data = QByteArray()
            data.append(json.dumps(tags))
            self.request_manager.post_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{configuration_id}/tags"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise AddTagException(f"Error while adding tag to configuration : {err}")

    def update_extra_and_name(
        self,
        datastore_id: str,
        configuration_id: str,
        name: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        """Update configuration extra and/or name

        :param datastore_id: datastore id
        :type datastore_id: str
        :param configuration_id: configuration id
        :type configuration_id: str
        :param name: new name, defaults to None
        :type name: Optional[str], optional
        :param extra: new extra dict, defaults to None
        :type extra: Optional[dict], optional
        :raises UpdateConfigurationException: error during request
        """
        self.log(
            f"{__name__}.update_extra_and_name({datastore_id=},{configuration_id=})"
        )

        if not name and not extra:
            return

        try:
            # encode data
            data = QByteArray()
            data_map = {
                "name": name,
            }
            if name is not None:
                data_map["name"] = name
            if extra is not None:
                data_map["extra"] = extra

            data.append(json.dumps(data_map))
            self.request_manager.patch_url(
                url=QUrl(
                    f"{self.get_base_url(datastore=datastore_id)}/{configuration_id}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise UpdateConfigurationException(
                f"Error in configuration update : {err}"
            ) from err

    def update_configuration(
        self,
        configuration: Configuration,
    ) -> None:
        """Update configuration
        :param configuration: configuration to update
        :type configuration: Configuration
        :raises UpdateConfigurationException: error when updating configuraiton
        """
        self.log(f"{__name__}.update_configuration(configuration: {configuration})")

        # encode data
        data = QByteArray()
        data_map = {
            "type": configuration.type.value,
            "metadata": [
                {"format": meta.format, "url": meta.url, "type": meta.type.value}
                for meta in configuration.metadata
            ],
            "name": configuration.name,
            "type_infos": configuration.type_infos,
        }
        if configuration.attribution:
            data_map["attribution"] = configuration.attribution
        data.append(json.dumps(data_map))
        try:
            # send request
            self.request_manager.put_url(
                url=QUrl(
                    f"{self.get_base_url(configuration.datastore_id)}/{configuration._id}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise UpdateConfigurationException(
                f"Error while updating configuration : {err}"
            )
