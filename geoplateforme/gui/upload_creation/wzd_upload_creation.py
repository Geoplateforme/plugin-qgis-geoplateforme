# standard
from qgis.PyQt.QtGui import QCloseEvent
from qgis.PyQt.QtWidgets import QWizard

# Plugin
from geoplateforme.gui.upload_creation.qwp_upload_creation import (
    UploadCreationPageWizard,
)
from geoplateforme.gui.upload_creation.qwp_upload_edition import UploadEditionPageWizard


class UploadCreationWizard(QWizard):
    def __init__(self, parent=None):
        """
        QWizard to for geoplateforme data import

        Args:
            parent: parent QObject
        """

        super().__init__(parent)
        self.setWindowTitle(self.tr("Upload creation"))

        self.qwp_upload_edition = UploadEditionPageWizard(self)
        self.qwp_upload_creation = UploadCreationPageWizard(
            qwp_upload_edition=self.qwp_upload_edition, parent=self
        )
        self.addPage(self.qwp_upload_edition)
        self.addPage(self.qwp_upload_creation)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)
        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)

    def set_datastore_id(self, datastore_id: str) -> None:
        """
        Define current datastore from datastore id

        Args:
            datastore_id: (str) datastore id
        """
        self.qwp_upload_edition.set_datastore_id(datastore_id)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Override closeEvent to check that current page is valid before close

        Args:
            event: QCloseEvent
        """
        # If upload creation page, check that page is valid
        current_page = self.currentPage()
        if current_page == self.qwp_upload_creation:
            if current_page.validatePage():
                event.accept()
            else:
                event.ignore()
        else:
            super().closeEvent(event)
