# standard
import os

from qgis.core import QgsProcessingException
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QWizardPage
from qgis.utils import OverrideCursor

# plugin
from geoplateforme.api.configuration import ConfigurationRequestManager
from geoplateforme.api.custom_exceptions import UnavailableConfigurationException
from geoplateforme.api.stored_data import (
    StoredDataStatus,
    StoredDataStep,
    StoredDataType,
)


class UpdatePublicationPageWizard(QWizardPage):
    def __init__(self, parent=None):
        """
        QWizardPage to update current geoplateforme publication

        Args:None

        """

        super().__init__(parent)

        self.setTitle(self.tr("Update the currrent publication"))
        uic.loadUi(
            os.path.join(
                os.path.dirname(__file__),
                "qwp_update_publication.ui",
            ),
            self,
        )

        # Only display pyramid generation ready for publication

        self.cbx_stored_data.set_filter_type([StoredDataType.PYRAMIDVECTOR])
        self.cbx_stored_data.set_visible_steps([StoredDataStep.PUBLISHED])
        self.cbx_stored_data.set_visible_status([StoredDataStatus.GENERATED])

        self.cbx_datastore.currentIndexChanged.connect(self._datastore_updated)
        self.cbx_stored_data.currentIndexChanged.connect(self._stored_data_updated)

        self._datastore_updated()

        self.setCommitPage(True)

    def set_datastore_id(self, datastore_id: str) -> None:
        """
        Define current datastore from datastore id

        Args:
            datastore_id: (str) datastore id
        """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.cbx_datastore.currentIndexChanged.disconnect(self._datastore_updated)
            self.cbx_datastore.set_datastore_id(datastore_id)
            self.cbx_datastore.currentIndexChanged.connect(self._datastore_updated)
            self._datastore_updated()

    def set_stored_data_id(self, stored_data_id: str) -> None:
        """
        Define current stored data from stored data id

        Args:
            stored_data_id: (str) stored data id
        """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.cbx_stored_data.currentIndexChanged.disconnect(
                self._stored_data_updated
            )
            self.cbx_stored_data.set_stored_data_id(stored_data_id)
            self.cbx_stored_data.currentIndexChanged.connect(self._stored_data_updated)
            self._stored_data_updated()

    def _datastore_updated(self) -> None:
        """
        Update pyramid generation combobox when datastore is updated

        """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.cbx_stored_data.currentIndexChanged.disconnect(
                self._stored_data_updated
            )
            self.cbx_stored_data.set_datastore(
                self.cbx_datastore.current_datastore_id()
            )
            self.cbx_stored_data.currentIndexChanged.connect(self._stored_data_updated)
            self._stored_data_updated()

    def _stored_data_updated(self) -> None:
        """
        Update pyramid generation combobox when datastore is updated

        """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            stored_data_id = self.cbx_stored_data.current_stored_data_id()
            datastore_id = self.cbx_datastore.current_datastore_id()
            if stored_data_id:
                try:
                    manager_config = ConfigurationRequestManager()
                    ids = manager_config.get_configurations_id(
                        datastore_id, stored_data_id
                    )
                    if len(ids) != 0:
                        configuration = manager_config.get_configuration(
                            datastore_id, ids[0]
                        )
                        self.wdg_publication_form.set_config(configuration)
                except UnavailableConfigurationException as exc:
                    raise QgsProcessingException(f"exc configuration : {exc}")
