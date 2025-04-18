# standard

from qgis.PyQt.QtWidgets import QDialog, QWizard

from geoplateforme.gui.publication_creation.qwp_publication_form import (
    PublicationFormPageWizard,
)
from geoplateforme.gui.publication_creation.qwp_status import PublicationStatut

# Plugin


class PublicationFormCreation(QWizard):
    def __init__(self, parent=None):
        """
        QWizard to for geoplateforme publication

        Args:
            parent: parent None
        """

        super().__init__(parent)
        self.setWindowTitle(self.tr("Publication creation"))
        self.qwp_publication_form = PublicationFormPageWizard(self)
        self.qwp_publication_status = PublicationStatut(self.qwp_publication_form, self)

        self.addPage(self.qwp_publication_form)
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
        self.qwp_publication_form.set_datastore_id(datastore_id)

    def set_stored_data_id(self, stored_data_id: str) -> None:
        """
        Define current stored data from stored data id

        Args:
            stored_data_id: (str) stored data id
        """
        self.qwp_publication_form.set_stored_data_id(stored_data_id)

    def accept(self) -> None:
        super().accept()
        if self.result() == QDialog.DialogCode.Accepted:
            self.restart()
