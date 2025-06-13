import os

from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QWidget

from geoplateforme.api.permissions import PermissionType
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.permissions.create_permission import (
    CreatePermissionAlgorithm,
)


class PermissionCreationDialog(QDialog):
    def __init__(self, datastore_id: str, parent: QWidget):
        """
        QDialog for permission creation

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "dlg_permission_creation.ui"),
            self,
        )
        self.datastore_id = datastore_id
        self.wdg_permission_creation.set_datastore_id(self.datastore_id)
        self.setWindowTitle(self.tr("Création d'une permission"))

    def accept(self) -> None:
        """Create permissions from creation widget.
        Dialog is not closed if an error occurs during creation
        """
        algo_str = (
            f"{GeoplateformeProvider().id()}:{CreatePermissionAlgorithm().name()}"
        )
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)

        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()

        params = {
            CreatePermissionAlgorithm.DATASTORE: self.datastore_id,
            CreatePermissionAlgorithm.LICENCE: self.wdg_permission_creation.get_licence(),
            CreatePermissionAlgorithm.PERMISSION_TYPE: self.wdg_permission_creation.get_permission_type().value,
            CreatePermissionAlgorithm.OFFERINGS: ",".join(
                self.wdg_permission_creation.get_offering_ids()
            ),
            CreatePermissionAlgorithm.ONLY_OAUTH: self.wdg_permission_creation.get_only_oauth(),
        }
        if self.wdg_permission_creation.get_permission_type() == PermissionType.ACCOUNT:
            params[CreatePermissionAlgorithm.USER_OR_COMMUNITIES] = ",".join(
                self.wdg_permission_creation.get_user_ids()
            )
        else:
            params[CreatePermissionAlgorithm.USER_OR_COMMUNITIES] = ",".join(
                self.wdg_permission_creation.get_community_ids()
            )
        if end_date := self.wdg_permission_creation.get_end_date():
            params[CreatePermissionAlgorithm.END_DATE] = end_date

        _, success = alg.run(params, context, feedback)

        if not success:
            QMessageBox.warning(
                self,
                self.tr("Erreur lors de la création des permissions."),
                feedback.textLog(),
            )
            return None

        return super().accept()
