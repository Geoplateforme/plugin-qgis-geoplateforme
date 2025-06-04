import json
import logging
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from tempfile import NamedTemporaryFile
from typing import List, Optional, Self
from xml.etree import ElementTree

# PyQGIS
from qgis.PyQt.QtCore import QByteArray, QCoreApplication, QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    AddTagException,
    DeleteMetadataException,
    DeleteTagException,
    ReadMetadataException,
    UnavailableMetadataException,
    UnavailableMetadataFileException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager

logger = logging.getLogger(__name__)


class MetadataType(Enum):
    INSPIRE = "INSPIRE"
    ISOAP = "ISOAP"


class MetadataLevel(Enum):
    DATASET = "DATASET"
    SERIES = "SERIES"


@dataclass
class MetadataFields:
    title: Optional[str] = None
    identifier: Optional[str] = None
    language: Optional[str] = None
    encoding: Optional[str] = None
    type: Optional[str] = None
    creation_date: Optional[datetime] = None
    abstract: Optional[str] = None
    org_name: Optional[str] = None
    org_email: Optional[str] = None
    inspire_keywords: Optional[List[str]] = None
    free_keywords: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    thumbnail: Optional[dict] = None
    frequency: Optional[str] = None
    resolution: Optional[int] = None
    bbox: Optional[dict] = None
    contact_email: Optional[str] = None
    update_date: Optional[datetime] = None
    genealogy: Optional[str] = None
    link: Optional[List[dict]] = None


@dataclass
class Metadata:
    _id: str
    datastore_id: str
    is_detailed: bool = False
    _fields: Optional[MetadataFields] = None
    # Optional
    _type: Optional[MetadataType] = None
    _open_data: Optional[bool] = None
    _level: Optional[MetadataLevel] = None
    _file_identifier: Optional[str] = None
    _tags: Optional[dict] = None
    _endpoints: Optional[List[dict]] = None
    _extra: Optional[dict] = None

    @property
    def type(self) -> MetadataType:
        """Returns the type of the metadata.

        :return: metadata type
        :rtype: MetadataType
        """
        if not self._type and not self.is_detailed:
            self.update_from_api()
        return self._type

    @property
    def open_data(self) -> bool:
        """Returns the open_data propertie of the metadata.

        :return: metadata open_data propertie
        :rtype: bool
        """
        if not self._open_data and not self.is_detailed:
            self.update_from_api()
        return self._open_data

    @property
    def level(self) -> MetadataLevel:
        """Returns the level of the metadata.

        :return: metadata level
        :rtype: MetadataLevel
        """
        if not self._level and not self.is_detailed:
            self.update_from_api()
        return self._level

    @property
    def file_identifier(self) -> str:
        """Returns the file_identifier of the metadata.

        :return: metadata file_identifier
        :rtype: str
        """
        if not self._file_identifier and not self.is_detailed:
            self.update_from_api()
        return self._file_identifier

    @property
    def tags(self) -> dict:
        """Returns the tags of the metadata.

        :return: metadata tags
        :rtype: dict
        """
        if not self._tags and not self.is_detailed:
            self.update_from_api()
        return self._tags

    @property
    def endpoints(self) -> List[dict]:
        """Returns the endpoints of the metadata.

        :return: metadata endpoints
        :rtype: List[dict]
        """
        if not self._endpoints and not self.is_detailed:
            self.update_from_api()
        return self._endpoints

    @property
    def extra(self) -> dict:
        """Returns the extra of the metadata.

        :return: metadata extra
        :rtype: dict
        """
        if not self._extra and not self.is_detailed:
            self.update_from_api()
        return self._extra

    @property
    def fields(self) -> MetadataFields:
        """Returns the metadata fields.

        :return: metadata fields
        :rtype: dict
        """
        if self._fields is None:
            self._fields = MetadataFields()
            self.update_metadata_fields()
        return self._fields

    def update_metadata_fields(self):
        """Update the metadata fields."""
        manager = MetadataRequestManager()
        meta_xml = manager.get_metadata_file(
            datastore_id=self.datastore_id, metadata_id=self._id
        )
        try:
            root = ElementTree.fromstring(meta_xml)
            if root is not None:
                identifier_field = root.find("./{*}fileIdentifier/{*}CharacterString")
                if identifier_field is not None:
                    self._fields.identifier = identifier_field.text

                language_field = root.find("./{*}language/{*}LanguageCode")
                if language_field is not None:
                    self._fields.language = language_field.attrib["codeListValue"]

                character_set_field = root.find(
                    "./{*}characterSet/{*}MD_CharacterSetCode"
                )
                if character_set_field is not None:
                    self._fields.encoding = character_set_field.text

                type_field = root.find("./{*}hierarchyLevel/{*}MD_ScopeCode")
                if type_field is not None:
                    self._fields.type = type_field.text

                ident_el = root.find("./{*}identificationInfo/{*}MD_DataIdentification")
                if ident_el is not None:
                    title_field = ident_el.find(
                        "./{*}citation/{*}CI_Citation/{*}title/{*}CharacterString"
                    )
                    if title_field is not None:
                        self._fields.title = title_field.text

                    creation_date_field = ident_el.find(
                        "./{*}citation/{*}CI_Citation/{*}date/{*}CI_Date/{*}date/{*}Date"
                    )
                    if creation_date_field is not None:
                        self._fields.creation_date = datetime.fromisoformat(
                            creation_date_field.text
                        )

                    abstract_field = ident_el.find("./{*}abstract/{*}CharacterString")
                    if abstract_field is not None:
                        self._fields.abstract = abstract_field.text

                    org_name_field = ident_el.find(
                        "./{*}pointOfContact/{*}CI_ResponsibleParty/{*}organisationName/{*}CharacterString"
                    )
                    if org_name_field is not None:
                        self._fields.org_name = org_name_field.text

                    org_email_field = ident_el.find(
                        "./{*}pointOfContact/{*}CI_ResponsibleParty/{*}contactInfo/{*}CI_Contact/{*}address/{*}CI_Address/{*}electronicMailAddress/{*}CharacterString"
                    )
                    if org_email_field is not None:
                        self._fields.org_email = org_email_field.text

                    all_keywords_field = ident_el.findall(
                        "./{*}descriptiveKeywords/{*}MD_Keywords"
                    )
                    if len(all_keywords_field) > 0:
                        self._fields.free_keywords = []
                        self._fields.inspire_keywords = []
                    for keywords_group in all_keywords_field:
                        keywords_field = keywords_group.findall(
                            "./{*}keyword/{*}CharacterString"
                        )
                        if len(keywords_field) > 0:
                            keywords = [kw.text for kw in keywords_field]
                            vocabulary_field = keywords_group.find(
                                "./{*}thesaurusName/{*}CI_Citation/{*}title/{*}CharacterString"
                            )
                            if vocabulary_field is not None:
                                for keyword in keywords:
                                    self._fields.inspire_keywords.append(keyword)
                            else:
                                for keyword in keywords:
                                    self._fields.free_keywords.append(keyword)

                    topics_field = ident_el.findall(
                        "./{*}topicCategory/{*}MD_TopicCategoryCode"
                    )
                    if len(topics_field) > 0:
                        self._fields.topics = []
                        for topic in topics_field:
                            self._fields.topics.append(topic.text)

                    thumbnail_field = ident_el.find(
                        "./{*}graphicOverview/{*}MD_BrowseGraphic"
                    )
                    if thumbnail_field is not None:
                        self._fields.thumbnail = {}
                        thumbnail_url = thumbnail_field.find(
                            "./{*}fileName/{*}CharacterString"
                        )
                        if thumbnail_url is not None:
                            self._fields.thumbnail["url"] = thumbnail_url.text
                        thumbnail_description = thumbnail_field.find(
                            "./{*}fileDescription/{*}CharacterString"
                        )
                        if thumbnail_description is not None:
                            self._fields.thumbnail["description"] = (
                                thumbnail_description.text
                            )
                        thumbnail_type = thumbnail_field.find(
                            "./{*}fileType/{*}CharacterString"
                        )
                        if thumbnail_type is not None:
                            self._fields.thumbnail["format"] = thumbnail_type.text

                    frequency_field = ident_el.find(
                        "./{*}resourceMaintenance/{*}MD_MaintenanceInformation/{*}maintenanceAndUpdateFrequency/{*}MD_MaintenanceFrequencyCode"
                    )
                    if frequency_field is not None:
                        self._fields.frequency = frequency_field.attrib["codeListValue"]

                    resolution_field = ident_el.find(
                        "./{*}spatialResolution/{*}MD_Resolution/{*}equivalentScale/{*}MD_RepresentativeFraction/{*}denominator/{*}Integer"
                    )
                    if resolution_field is not None:
                        self._fields.resolution = int(resolution_field.text)

                    bbox_field = ident_el.find(
                        "./{*}extent/{*}EX_Extent/{*}geographicElement/{*}EX_GeographicBoundingBox"
                    )
                    if bbox_field is not None:
                        self._fields.bbox = {}
                        westBoundLongitude = bbox_field.find(
                            "./{*}westBoundLongitude/{*}Decimal"
                        )
                        if westBoundLongitude is not None:
                            self._fields.bbox["xmin"] = float(westBoundLongitude.text)
                        eastBoundLongitude = bbox_field.find(
                            "./{*}eastBoundLongitude/{*}Decimal"
                        )
                        if eastBoundLongitude is not None:
                            self._fields.bbox["xmax"] = float(eastBoundLongitude.text)
                        southBoundLatitude = bbox_field.find(
                            "./{*}southBoundLatitude/{*}Decimal"
                        )
                        if southBoundLatitude is not None:
                            self._fields.bbox["ymin"] = float(southBoundLatitude.text)
                        northBoundLatitude = bbox_field.find(
                            "./{*}northBoundLatitude/{*}Decimal"
                        )
                        if northBoundLatitude is not None:
                            self._fields.bbox["ymax"] = float(northBoundLatitude.text)

                    contact_email_field = root.find(
                        "./{*}contact/{*}CI_ResponsibleParty/{*}contactInfo/{*}CI_Contact/{*}address/{*}CI_Address/{*}electronicMailAddress/{*}CharacterString"
                    )
                    if contact_email_field is not None:
                        self._fields.contact_email = contact_email_field.text

                    update_date_field = root.find("./{*}dateStamp/{*}DateTime")
                    if (
                        update_date_field is not None
                        and update_date_field.text is not None
                    ):
                        self._fields.update_date = datetime.fromisoformat(
                            update_date_field.text
                        )

                    genealogy_field = root.find(
                        "./{*}dataQualityInfo/{*}DQ_DataQuality/{*}lineage/{*}LI_Lineage/{*}statement/{*}CharacterString"
                    )
                    if genealogy_field is not None:
                        self._fields.genealogy = genealogy_field.text

                    distribution_field = root.find(
                        "./{*}distributionInfo/{*}MD_Distribution/{*}transferOptions/{*}MD_DigitalTransferOptions"
                    )
                    if distribution_field is not None:
                        links_field = distribution_field.findall("./{*}onLine")
                        if len(links_field) > 0:
                            self._fields.link = []
                        for link_field in links_field:
                            link = {}
                            if link_field.attrib["type"] == "offering":
                                link["type"] = "Web Service"
                            if link_field.attrib["type"] == "style":
                                link["type"] = "Style"
                            if link_field.attrib["type"] == "getcapabilities":
                                link["type"] = "GetCapabilities"
                            if link_field.attrib["type"] == "document":
                                link["type"] = "Document"

                            link_name = link_field.find(
                                "./{*}CI_OnlineResource/{*}name/{*}CharacterString"
                            )
                            if link_name is not None:
                                link["name"] = link_name.text
                            link_url = link_field.find(
                                "./{*}CI_OnlineResource/{*}linkage/{*}URL"
                            )
                            if link_url is not None:
                                link["url"] = link_url.text
                            link_type = link_field.find(
                                "./{*}CI_OnlineResource/{*}protocol/{*}CharacterString"
                            )
                            if link_type is not None:
                                link["format"] = link_type.text
                            link_description = link_field.find(
                                "./{*}CI_OnlineResource/{*}description/{*}CharacterString"
                            )
                            if link_description is not None:
                                link["description"] = link_description.text
                            self._fields.link.append(link)
        except Exception as err:
            raise ReadMetadataException(err)

    def update_from_api(self):
        """Update the metadata by calling API details."""
        manager = MetadataRequestManager()
        data = manager.get_metadata_json(self.datastore_id, self._id)

        if "type" in data:
            self._type = MetadataType(data["type"])
        if "open_data" in data:
            self._open_data = data["open_data"]
        if "level" in data:
            self._level = MetadataLevel(data["level"])
        if "file_identifier" in data:
            self._file_identifier = data["file_identifier"]
        if "tags" in data:
            self._tags = data["tags"]
        if "endpoints" in data:
            self._endpoints = data["endpoints"]
        if "extra" in data:
            self._extra = data["extra"]

        self.is_detailed = True

    @classmethod
    def from_dict(cls, datastore_id: str, val: dict) -> Self:
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

        if "type" in val:
            res._type = MetadataType(val["type"])
        if "open_data" in val:
            res._open_data = val["open_data"]
        if "level" in val:
            res._level = MetadataLevel(val["level"])
        if "file_identifier" in val:
            res._file_identifier = val["file_identifier"]
        if "tags" in val:
            res._tags = val["tags"]
        if "endpoints" in val:
            res._endpoints = val["endpoints"]
        if "extra" in val:
            res._extra = val["extra"]

        return res


class MetadataRequestManager:
    MAX_LIMIT: int = 50

    def __init__(self):
        """
        Helper for metadata request

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
        Get base url for metadata for a datastore

        Args:
            datastore: (str) datastore id

        Returns: url for metadata

        """
        return (
            f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore}/metadata"
        )

    def get_metadata_list(
        self,
        datastore_id: str,
        tags: Optional[dict] = None,
    ) -> List[Metadata]:
        """Get list of metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadMetadataException: when error occur during requesting the API

        :return: list of available metadata
        :rtype: List[Metadata]
        """
        self.log(f"{__name__}.get_metadata_list(datastore:{datastore_id})")
        nb_value = self._get_nb_available_metadata(datastore_id, tags)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_metadata_list(
                datastore_id, page + 1, self.MAX_LIMIT, tags
            )
        return result

    def _get_metadata_list(
        self,
        datastore_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
        tags: Optional[dict] = None,
    ) -> List[Metadata]:
        """Get list of metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadMetadataException: when error occur during requesting the API

        :return: list of available metadata
        :rtype: List[Metadata]
        """

        # Add filter on tags
        tags_url = ""
        if tags:
            for key, value in dict.items(tags):
                tags_url += f"&tags[{key}]={value}"

        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}?page={page}&limit={limit}{tags_url}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadMetadataException(f"Error while fetching metadata : {err}")

        data = json.loads(reply.data())

        return [Metadata.from_dict(datastore_id, metadata) for metadata in data]

    def _get_nb_available_metadata(
        self, datastore_id: str, tags: Optional[dict] = None
    ) -> int:
        """Get number of available metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param tags: list of tags to filter data
        :type tags: dict, optional

        :raises ReadMetadataException: when error occur during requesting the API

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
            raise ReadMetadataException(f"Error while fetching metadata: {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadMetadataException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def get_metadata(self, datastore_id: str, metadata_id: str) -> Metadata:
        """Get metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata_id: metadata id
        :type metadata_id: str

        :raises UnavailableMetadataException: when error occur during requesting the API

        :return: Metadata if available
        :rtype: Metadata
        """
        self.log(
            f"{__name__}.get_metadata(datastore:{datastore_id}, metadata: {metadata_id})"
        )

        return Metadata.from_dict(
            datastore_id, self.get_metadata_json(datastore_id, metadata_id)
        )

    def get_metadata_json(self, datastore_id: str, metadata_id: str) -> dict:
        """Get dict values of metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata_id: metadata id
        :type metadata_id: str

        :raises UnavailableMetadataException: when error occur during requesting the API

        :return: dict values of metadata
        :rtype: dict
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{metadata_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
            return json.loads(reply.data())
        except ConnectionError as err:
            raise UnavailableMetadataException(f"Error while fetching metadata : {err}")

    def delete(self, datastore_id: str, metadata_id: str) -> None:
        """Delete an metadata.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata_id: metadata id
        :type metadata_id: str

        :raises DeleteMetadataException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.delete(datastore:{datastore_id}, metadata: {metadata_id})"
        )

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{metadata_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteMetadataException(f"Error while deleting metadata : {err}.")

    def add_tags(self, datastore_id: str, metadata_id: str, tags: dict) -> None:
        """Add tags to metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata_id: metadata id
        :type metadata_id: str
        :param tags: dictionary of tags
        :type tags: dict

        :raises AddTagException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.add_tags(datastore:{datastore_id},metadata:{metadata_id}, tags:{tags})"
        )

        try:
            # encode data
            data = QByteArray()
            data.append(json.dumps(tags))
            self.request_manager.post_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{metadata_id}/tags"),
                config_id=self.plg_settings.qgis_auth_id,
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            raise AddTagException(f"Error while adding tag to metadata : {err}")

    def delete_tags(self, datastore_id: str, metadata_id: str, tags: list[str]) -> None:
        """Delete tags of metadata

        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata_id: metadata id
        :type metadata_id: str
        :param tags: list of tags to delete
        :type tags: list[str]

        :raises DeleteTagException: when error occur during requesting the API
        """
        self.log(
            f"{__name__}.delete_tags(datastore:{datastore_id},metadata:{metadata_id}, tags:{tags})"
        )

        url = f"{self.get_base_url(datastore_id)}/{metadata_id}/tags?"
        # Add all tag to remove
        for tag in tags:
            url += f"&tags={tag}"

        try:
            self.request_manager.delete_url(
                url=QUrl(url),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteTagException(f"Error while deleting tags for metadata : {err}")

    # TODO :
    # def create_metadata(
    #     self,
    #     datastore_id: str,
    #     open_data: bool,
    #     metadata_type: MetadataType,
    #     filename: str
    # ) -> Metadata:
    #     """Create metadata on Geoplateforme entrepot

    #     :param datastore_id: datastore id
    #     :type datastore_id: str
    #     :param open_data: metadata open_data propertie
    #     :type open_data: bool
    #     :param metadata_type: metadata type
    #     :type metadata_type: MetadataType
    #     :param filename: metadata file to import
    #     :type filename: str

    #     :raises MetadataCreationException: when error occur during requesting the API

    #     :return: Metadata if creation succeeded
    #     :rtype: Metadata
    #     """
    #     self.log(
    #         f"{__name__}.create_metadata(datastore:{datastore_id}, open_data: {open_data}, type: {metadata_type}, filename: {filename})"
    #     )

    #     try:
    #         # encode data
    #         data = QByteArray()
    #         data_map = {
    #             "open_data": open_data,
    #             "type": metadata_type.value,
    #         }
    #         data.append(json.dumps(data_map))
    #         reply = self.request_manager.post_url(
    #             url=QUrl(self.get_base_url(datastore_id)),
    #             config_id=self.plg_settings.qgis_auth_id,
    #             data=data,
    #             headers={b"Content-Type": bytes("application/json", "utf8")},
    #         )
    #     except ConnectionError as err:
    #         raise MetadataCreationException(f"Error while creating metadata : {err}")

    #     # check response type
    #     data = json.loads(reply.data())
    #     return Metadata.from_dict(datastore_id, data)

    def get_metadata_file(self, datastore_id: str, metadata_id: str) -> str:
        """Get metadata file.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata_id: metadata id
        :type metadata_id: str

        :raises UnavailableMetadataFileException: when error occur during requesting the API

        :return: Metadata file if available
        :rtype: dict
        """
        self.log(
            f"{__name__}.get_metadata_file(datastore:{datastore_id}, metadata: {metadata_id})"
        )

        try:
            # Define temporary file name
            temp_file_name = NamedTemporaryFile(suffix=".xml").name
            # Can't directly use with to download file
            # because a lock is added to temp file on windows
            self.request_manager.download_file_to(
                remote_url=QUrl(
                    f"{self.get_base_url(datastore_id)}/{metadata_id}/file"
                ),
                auth_cfg=self.plg_settings.qgis_auth_id,
                local_path=temp_file_name,
            )
            # Load data
            with open(temp_file_name) as tmp_file:
                data = tmp_file.read()
            # Delete temporary file
            os.remove(temp_file_name)
        except ConnectionError as err:
            raise UnavailableMetadataFileException(
                f"Error while fetching metadata file : {err}"
            )
        return data
