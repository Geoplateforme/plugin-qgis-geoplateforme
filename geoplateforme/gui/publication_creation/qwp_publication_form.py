# standard
import os

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWizardPage


class PublicationFormPageWizard(QWizardPage):
    def __init__(
        self,
        parent=None,
    ):
        """
        QWizardPage to define current geoplateforme publication

        Args:
            parent: parent None

        """

        super().__init__(parent)
        self.setTitle(self.tr("Describe and publish your tiles"))

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "qwp_publication_form.ui"), self
        )

    def validatePage(self) -> bool:
        """
        Validate current page content by checking files

        Returns: True

        """

        return self.wdg_publication_form.validatePage()
