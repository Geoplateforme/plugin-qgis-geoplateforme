#! python3

# Standard library
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

# PyQGIS
from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    AnnexeFileUploadException,
    DeleteAnnexeException,
    ReadAnnexeException,
    UnavailableAnnexeFileException,
)
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


@dataclass
class Annexe:
    _id: str
    datastore_id: str
    paths: list[str]
    size: int
    mime_type: str
    published: bool
    labels: Optional[list[str]] = None
    extra: Optional[dict] = None

    @classmethod
    def from_dict(cls, datastore_id: str, val: dict) -> Annexe:
        """Load object from a dict.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param val: dict value to load
        :type val: dict

        :return: object with attributes filled from dict.
        :rtype: Annex
        """
        res = cls(
            _id=val["_id"],
            datastore_id=datastore_id,
            paths=val["paths"],
            size=val["size"],
            mime_type=val["mime_type"],
            published=val["published"],
        )
        if "labels" in val:
            res.labels = val["labels"]
        if "extra" in val:
            res.labels = val["extra"]
        return res


class AnnexeRequestManager:
    MAX_LIMIT = 50

    def __init__(self):
        """Helper for stored_data request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_base_url(self, datastore_id: str) -> str:
        """Get base url for static for a datastore

        :param datastore_id: datastore id
        :type datastore_id: str

        :return: url for static
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/datastores/{datastore_id}/annexes"

    def get_annexe_list(
        self,
        datastore_id: str,
        labels: Optional[List[str]] = None,
    ) -> List[Annexe]:
        """Get list of annexe

        :param datastore_id: datastore id
        :type datastore_id: str
        :param labels: list of labels to filter data
        :type labels: List[str], optional

        :raises ReadAnnexeException: when error occur during requesting the API

        :return: list of available annexe
        :rtype: List[Annexe]
        """
        self.log(f"{__name__}.get_annexe_list(datastore:{datastore_id})")
        nb_value = self._get_nb_available_annexe(datastore_id, labels)
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_annexe_list(
                datastore_id, page + 1, self.MAX_LIMIT, labels
            )
        return result

    def _get_annexe_list(
        self,
        datastore_id: str,
        page: int = 1,
        limit: int = MAX_LIMIT,
        labels: Optional[List[str]] = None,
    ) -> List[Annexe]:
        """Get list of annexe

        :param datastore_id: datastore id
        :type datastore_id: str
        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int
        :param labels: list of labels to filter data
        :type labels: List[str], optional

        :raises ReadAnnexeException: when error occur during requesting the API

        :return: list of available annexe
        :rtype: List[Annexe]
        """

        # Add filter on labels
        labels_url = ""
        if labels:
            for value in labels:
                labels_url += f"&labels={value}"

        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url(datastore_id)}?page={page}&limit={limit}{labels_url}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadAnnexeException(f"Error while fetching annexe : {err}")

        data = json.loads(reply.data())

        return [Annexe.from_dict(datastore_id, annexe) for annexe in data]

    def _get_nb_available_annexe(
        self, datastore_id: str, labels: Optional[List[str]] = None
    ) -> int:
        """Get number of available annexe

        :param datastore_id: datastore id
        :type datastore_id: str
        :param labels: list of labels to filter data
        :type labels: List[str], optional

        :raises ReadAnnexeException: when error occur during requesting the API

        :return: number of available data
        :rtype: int
        """
        # For now read with maximum limit possible
        labels_url = ""
        if labels:
            for value in labels:
                labels_url += f"&labels={value}"
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}?limit=1{labels_url}"),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadAnnexeException(f"Error while fetching annexe: {err}")

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadAnnexeException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val

    def create_annexe(
        self,
        datastore_id: str,
        file_path: Path,
        public_paths: list[str],
        published: bool,
        labels: list[str],
    ) -> Annexe:
        """Create annex in datastore

        :param datastore_id: datastore id
        :type datastore_id: str
        :param file_path: path to annex file
        :type file_path: Path
        :param public_paths: public path in datastore
        :type public_paths: list[str]
        :param published: True to publish annex, False otherwise
        :type published: bool
        :param labels: list of labels
        :type labels: list[str]
        :raises AnnexeFileUploadException: error in request
        :return: created annex
        :rtype: Annexe
        """
        self.log(
            f"{__name__}.create_annexe({datastore_id=},{file_path=},{public_paths=},{published=},{labels=})"
        )

        try:
            data = {
                "paths": public_paths,
                "published": published,
                "labels": labels,
            }
            reply = self.request_manager.post_file(
                url=QUrl(f"{self.get_base_url(datastore_id)}"),
                config_id=self.plg_settings.qgis_auth_id,
                file_path=file_path,
                data=data,
            )
        except ConnectionError as err:
            raise AnnexeFileUploadException(f"Error while posting annexe file : {err}")

        data = json.loads(reply.data())
        return Annexe.from_dict(datastore_id, data)

    def delete(self, datastore_id: str, annexe_id: str) -> None:
        """Delete an annex.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param annexe_id: annexe id
        :type annexe_id: str

        :raises DeleteAnnexeException: when error occur during requesting the API
        """
        self.log(f"{__name__}.delete({datastore_id=},{annexe_id=})")

        try:
            self.request_manager.delete_url(
                url=QUrl(f"{self.get_base_url(datastore_id)}/{annexe_id}"),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise DeleteAnnexeException(f"Error while deleting annexe: {err}.")

    def get_annexe_file(self, datastore_id: str, annexe_id: str) -> str:
        """Get annexe file.

        :param datastore_id: datastore id
        :type datastore_id: str
        :param annexe_id: annexe id
        :type annexe_id: str

        :raises UnavailableAnnexeFileException: when error occur during requesting the API

        :return: Annexe file if available
        :rtype: dict
        """
        self.log(
            f"{__name__}.get_annexe_file(datastore:{datastore_id}, annexe: {annexe_id})"
        )

        try:
            # Define temporary file name
            temp_file_name = NamedTemporaryFile(suffix=".xml").name
            # Can't directly use with to download file
            # because a lock is added to temp file on windows
            self.request_manager.download_file_to(
                remote_url=QUrl(f"{self.get_base_url(datastore_id)}/{annexe_id}/file"),
                auth_cfg=self.plg_settings.qgis_auth_id,
                local_path=temp_file_name,
            )
            # Load data
            with open(temp_file_name) as tmp_file:
                data = tmp_file.read()
            # Delete temporary file
            os.remove(temp_file_name)
        except ConnectionError as err:
            raise UnavailableAnnexeFileException(
                f"Error while fetching annexe file : {err}"
            )
        return data
