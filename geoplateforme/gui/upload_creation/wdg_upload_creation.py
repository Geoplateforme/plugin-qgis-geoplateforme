# standard
import os
from pathlib import Path
from typing import List

from osgeo import ogr

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt import QtCore, uic
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

    def get_multi_geom_layers_str(self) -> str:
        """Return string for multi geom layers

        :return: multi geom layers string
        :rtype: str
        """
        return self.lne_multi_geom_table.text()

    def validateWidget(self) -> bool:
        """
        Validate current content by checking files

        Returns: True if content is valid, False otherwise

        """
        if self.cb_check_data.isChecked():
            valid = self._check_input_layers()
        else:
            valid = True

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

    def _get_input_layers_for_check(self) -> list[QgsVectorLayer]:
        """Get list of layer for check from selected files and QGIS layer

        :return: input layers for check
        :rtype: list[QgsVectorLayer]
        """
        input_file = self.get_filenames()
        input_layers = self.get_layers()
        for file in input_file:
            layer = QgsVectorLayer(file)
            if layer.isValid():
                filename = layer.dataProvider().dataSourceUri()
                fileinfo = QtCore.QFileInfo(filename)
                if fileinfo.exists() and fileinfo.suffix() == "gpkg":
                    gpkg_layers = [
                        gpkg_layer.GetName() for gpkg_layer in ogr.Open(filename)
                    ]
                    for layer_name in gpkg_layers:
                        input_layers.append(
                            QgsVectorLayer(
                                f"{filename}|layername={layer_name}", layer_name
                            )
                        )
                else:
                    input_layers.append(layer)
        return input_layers

    def _check_input_layers(self) -> bool:
        valid = True

        algo_str = f"{GeoplateformeProvider().id()}:{CheckLayerAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)

        params = {CheckLayerAlgorithm.INPUT_LAYERS: self._get_input_layers_for_check()}
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
            if CheckLayerAlgorithm.ResultCode.INVALID_GEOMETRY in result_code:
                error_string += self.tr("- invalid geometry\n")
            if CheckLayerAlgorithm.ResultCode.NO_FEATURES in result_code:
                error_string += self.tr("- no feature available\n")

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

        # Define automatic multigeom layer names
        multi_geom_layer_names = self._get_multigeom_layer_names()
        self.lne_multi_geom_table.setText(",".join(multi_geom_layer_names))

    def _get_multigeom_layer_names(self) -> list[str]:
        """Get multigeom layer names from selected files and layers

        :return: multigeom layer names
        :rtype: list[str]
        """
        input_layers = self._get_input_layers_for_check()

        multi_geom_layer = []
        for layer in input_layers:
            if QgsWkbTypes.isMultiType(layer.wkbType()):
                storage_type = layer.storageType()
                if storage_type == "ESRI Shapefile" or storage_type == "GeoJSON":
                    multi_geom_layer.append(Path(layer.source()).stem)
                else:
                    multi_geom_layer.append(layer.name())
        return multi_geom_layer
