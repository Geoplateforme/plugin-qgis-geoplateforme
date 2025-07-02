import os

from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QWidget

from geoplateforme.processing.provider import GeoplateformeProvider
from geoplateforme.processing.user_key.create_accesses import CreateAccessesAlgorithm


class UserKeyCreationDialog(QDialog):
    def __init__(self, parent: QWidget):
        """
        QDialog for user key creation

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "dlg_user_key_creation.ui"),
            self,
        )
        self.setWindowTitle(self.tr("Création d'une clé"))

    def accept(self) -> None:
        """Create user key from creation widget.
        Dialog is not closed if an error occurs during creation
        """
        selected_offering_and_permission = (
            self.wdg_user_key_creation.get_selected_permission_and_offering()
        )
        if len(selected_offering_and_permission) == 0:
            QMessageBox.warning(
                self,
                self.tr("Aucun service sélectionné"),
                self.tr("Veuillez choisir au moins un accès à un service."),
            )
            return None

        algo_str = self.wdg_user_key_creation.get_creation_algo_str()
        params = self.wdg_user_key_creation.get_creation_parameters()

        alg = QgsApplication.processingRegistry().algorithmById(algo_str)

        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()

        result, success = alg.run(params, context, feedback)

        if not success:
            QMessageBox.warning(
                self,
                self.tr("Erreur lors de la création de la clé."),
                feedback.textLog(),
            )
            return None

        # Add access to the selected offerings
        for permission, offerings in selected_offering_and_permission:
            algo_str = (
                f"{GeoplateformeProvider().id()}:{CreateAccessesAlgorithm().name()}"
            )
            alg = QgsApplication.processingRegistry().algorithmById(algo_str)

            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()

            params = {
                CreateAccessesAlgorithm.KEY_ID: result["CREATED_KEY_ID"],
                CreateAccessesAlgorithm.PERMISSION_ID: permission._id,
                CreateAccessesAlgorithm.OFFERING_IDS: ",".join(
                    [offering._id for offering in offerings]
                ),
            }
            _, success = alg.run(params, context, feedback)

            if not success:
                QMessageBox.warning(
                    self,
                    self.tr("Erreur lors de l'ajout des accès sur la clé."),
                    self.tr(
                        "Les accès n'ont pas été correctement ajoutés. Veuillez vérifier la clé créé:\n {}".format(
                            feedback.textLog()
                        )
                    ),
                )

        # Ask for QGIS authentication creation
        self.wdg_user_key_creation.create_qgis_auth(result)

        return super().accept()
