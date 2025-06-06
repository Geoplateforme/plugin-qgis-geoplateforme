# standard
import os
from typing import List

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsVectorLayer,
)
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QMessageBox, QWidget

# Plugin
from geoplateforme.gui.lne_validators import alphanum_qval
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.check_layer import CheckLayerAlgorithm


class UploadCreationWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        """
        Widget to display information for upload creation

        Args:
            parent: (QWidget) parent
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_upload_creation.ui"), self
        )

        # To avoid some characters
        self.lne_data.setValidator(alphanum_qval)
        self.lne_dataset.setValidator(alphanum_qval)

        self.wdg_layer_selection.selection_updated.connect(self._selection_updated)

    def get_name(self) -> str:
        """
        Get defined name

        Returns: (str) defined name

        """
        return self.lne_data.text()

    def get_dataset_name(self) -> str:
        """
        Get defined name

        Returns: (str) defined name

        """
        return self.lne_dataset.text()

    def set_name(self, name: str) -> None:
        """
        Define name

        Args:
            name: (str)
        """
        self.lne_data.setText(name)

    def set_dataset_name(self, name: str) -> None:
        """
        Define dataset_name

        Args:
            name: (str)
        """
        self.lne_dataset.setText(name)

    def get_crs(self) -> str:
        """
        Get defined crs auth id

        Returns: (str) defined crs auth id

        """
        return self.psw_projection.crs().authid()

    def get_filenames(self) -> [str]:
        """
        Get selected filenames

        Returns: selected filenames

        """
        return self.wdg_layer_selection.get_filenames()

    def get_layers(self) -> List[QgsVectorLayer]:
        """Return selected QgsVectorLayer

        :return: selected layer
        :rtype: List[QgsVectorLayer]
        """
        return self.wdg_layer_selection.get_layers()

    def validateWidget(self) -> bool:
        """
        Validate current content by checking files

        Returns: True if content is valid, False otherwise

        """
        valid = self._check_input_layers()

        if valid and len(self.lne_dataset.text()) == 0:
            valid = False
            QMessageBox.warning(
                self,
                self.tr("No dataset name defined."),
                self.tr("Please define dataset name"),
            )

        if valid and len(self.lne_data.text()) == 0:
            valid = False
            QMessageBox.warning(
                self, self.tr("No name defined."), self.tr("Please define data name")
            )

        if valid and not self.psw_projection.crs().isValid():
            valid = False
            QMessageBox.warning(
                self, self.tr("No SRS defined."), self.tr("Please define SRS")
            )

        return valid

    def _check_input_layers(self) -> bool:
        valid = True

        algo_str = f"{GeoplateformeProvider().id()}:{CheckLayerAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)

        params = {CheckLayerAlgorithm.INPUT_LAYERS: self.get_filenames()}
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        result, success = alg.run(params, context, feedback)

        result_code = result[CheckLayerAlgorithm.RESULT_CODE]

        if result_code != CheckLayerAlgorithm.ResultCode.VALID:
            valid = False
            error_string = self.tr("Invalid layers:\n")
            if CheckLayerAlgorithm.ResultCode.CRS_MISMATCH in result_code:
                error_string += self.tr("- CRS mismatch\n")
            if CheckLayerAlgorithm.ResultCode.INVALID_LAYER_NAME in result_code:
                error_string += self.tr("- invalid layer name\n")
            if CheckLayerAlgorithm.ResultCode.INVALID_FILE_NAME in result_code:
                error_string += self.tr("- invalid file name\n")
            if CheckLayerAlgorithm.ResultCode.INVALID_FIELD_NAME in result_code:
                error_string += self.tr("- invalid field name\n")
            if CheckLayerAlgorithm.ResultCode.INVALID_LAYER_TYPE in result_code:
                error_string += self.tr("- invalid layer type\n")

            error_string += self.tr("Invalid layers list are available in details.")

            msgBox = QMessageBox(
                QMessageBox.Icon.Warning, self.tr("Invalid layers"), error_string
            )
            msgBox.setDetailedText(feedback.textLog())
            msgBox.exec()

        return valid

    def _selection_updated(self) -> None:
        # Define name if empty
        if not self.lne_data.text():
            self.lne_data.setText(self.wdg_layer_selection.get_first_displayed_name())

        # Define CRS if not defined
        if (
            not self.psw_projection.crs().isValid()
            and self.wdg_layer_selection.get_first_crs()
        ):
            self.psw_projection.setCrs(
                QgsCoordinateReferenceSystem(self.wdg_layer_selection.get_first_crs())
            )
            self.psw_projection.update()
