# standard
from typing import Optional

# PyQGIS
from qgis.PyQt.QtWidgets import QWizard

from geoplateforme.gui.publication.qwp_visibility import VisibilityPageWizard
from geoplateforme.gui.qwp_metadata_form import MetadataFormPageWizard
from geoplateforme.gui.wfs_publication.qwp_publication_form import (
    PublicationFormPageWizard,
)

# Plugin
from geoplateforme.gui.wfs_publication.qwp_table_relation import TableRelationPageWizard
from geoplateforme.gui.wfs_publication.qwp_wfs_publication_status import (
    PublicationStatut,
)


class WFSPublicationWizard(QWizard):
    def __init__(
        self,
        parent=None,
        datastore_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        stored_data_id: Optional[str] = None,
    ):
        """
        QWizard for WFS publication

        Args:
            parent: parent None
            datastore_id: datastore id
            dataset_name: dataset name
            stored_data_id: store data id
        """

        super().__init__(parent)
        self.setWindowTitle(self.tr("Publication WFS"))

        # First page to define stored data and table relation
        self.qwp_table_relation = TableRelationPageWizard(
            self, datastore_id, dataset_name, stored_data_id
        )

        # Second page to display publication form
        self.qwp_publication_form = PublicationFormPageWizard()

        # Third page for metadata
        self.qwp_metadata_form = MetadataFormPageWizard(
            datastore_id, dataset_name, self
        )
        # Fourth page to define visibility
        self.qwp_visibility = VisibilityPageWizard(self)

        # Last page to launch processing and display results
        self.qwp_publication_status = PublicationStatut(
            self.qwp_table_relation,
            self.qwp_publication_form,
            self.qwp_metadata_form,
            self.qwp_visibility,
            self,
        )

        self.addPage(self.qwp_table_relation)
        self.addPage(self.qwp_publication_form)
        self.addPage(self.qwp_metadata_form)
        self.addPage(self.qwp_visibility)
        self.addPage(self.qwp_publication_status)

        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)
        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)

    def set_datastore_id(self, datastore_id: str) -> None:
        """
        Define current datastore from datastore id

        Args:
            datastore_id: (str) datastore id
        """
        self.qwp_table_relation.set_datastore_id(datastore_id)

    def set_dataset_name(self, dataset_name: str) -> None:
        """
        Define current dataset name

        Args:
            dataset_name: (str) dataset name
        """
        self.qwp_table_relation.set_dataset_name(dataset_name)

    def set_stored_data_id(self, stored_data_id: str) -> None:
        """
        Define current stored data from stored data id

        Args:
            stored_data_id: (str) stored data id
        """
        self.qwp_table_relation.set_stored_data_id(stored_data_id)

    def get_offering_id(self) -> str:
        """Get offering id of created service

        :return: offering id
        :rtype: str
        """
        return self.qwp_publication_status.offering_id
