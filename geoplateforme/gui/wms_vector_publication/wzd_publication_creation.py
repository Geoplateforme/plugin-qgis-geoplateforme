# standard
from typing import Optional

# PyQGIS
from qgis.PyQt.QtWidgets import QWizard

# Plugin
from geoplateforme.api.stored_data import StoredData
from geoplateforme.gui.publication.qwp_visibility import VisibilityPageWizard
from geoplateforme.gui.qwp_metadata_form import MetadataFormPageWizard
from geoplateforme.gui.wms_vector_publication.qwp_publication_form import (
    PublicationFormPageWizard,
)
from geoplateforme.gui.wms_vector_publication.qwp_table_style_selection import (
    TableRelationPageWizard,
)
from geoplateforme.gui.wms_vector_publication.qwp_wms_vector_publication_status import (
    PublicationStatut,
)


class WMSVectorPublicationWizard(QWizard):
    def __init__(
        self,
        stored_data: StoredData,
        parent=None,
        datastore_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ):
        """
        QWizard for WMS-VECTOR publication

        Args:
            stored_data: stored data
            parent: parent None
            datastore_id: datastore id
            dataset_name: dataset name
        """

        super().__init__(parent)
        self.setWindowTitle(self.tr("Publication WMS-Vecteur"))

        stored_data_id = stored_data._id

        # First page to define stored data and table relation
        self.qwp_table_relation = TableRelationPageWizard(stored_data, self)

        # Second page to display publication form
        self.qwp_publication_form = PublicationFormPageWizard()

        # Third page to display metadata
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
            datastore_id,
            dataset_name,
            stored_data_id,
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

    def get_offering_id(self) -> str:
        """Get offering id of created service

        :return: offering id
        :rtype: str
        """
        return self.qwp_publication_status.offering_id

    def reject(self) -> None:
        """Override reject to check last page and wait for metadata publication"""
        # If service publication page, check that page is valid
        current_page = self.currentPage()
        if current_page == self.qwp_publication_status:
            if current_page.validatePage():
                super().reject()
        else:
            super().reject()
