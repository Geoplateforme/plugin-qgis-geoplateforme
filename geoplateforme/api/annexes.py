import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import (
    AnnexeFileUploadException,
    DeleteAnnexeException,
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
    def from_dict(cls, datastore_id: str, val: dict):
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
