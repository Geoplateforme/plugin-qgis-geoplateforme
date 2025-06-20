import re
from enum import IntFlag
from typing import List

from osgeo import ogr
from qgis.core import (
    QgsMapLayer,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingFeedback,
    QgsProcessingOutputNumber,
    QgsProcessingParameterMultipleLayers,
    QgsVectorLayer,
)
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QCoreApplication

from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class CheckLayerAlgorithm(QgsProcessingAlgorithm):
    INPUT_LAYERS = "INPUT_LAYERS"
    RESULT_CODE = "RESULT_CODE"

    class ResultCode(IntFlag):
        """
        https://docs.python.org/fr/3/library/enum.html#intflag
        """

        VALID = 0
        CRS_MISMATCH = 1
        INVALID_LAYER_NAME = 2
        INVALID_FILE_NAME = 4
        INVALID_FIELD_NAME = 8
        INVALID_LAYER_TYPE = 16

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return CheckLayerAlgorithm()

    def name(self):
        return "check_layer"

    def displayName(self):
        return self.tr("Check layers for IGN Geoplateforme")

    def group(self):
        return self.tr("Outils géoplateforme")

    def groupId(self):
        return "tools"

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                name=self.INPUT_LAYERS,
                layerType=QgsProcessing.SourceType.TypeVectorAnyGeometry,
                description=self.tr("Couches vectorielles à vérifier"),
                optional=True,
            )
        )

        self.addOutput(
            QgsProcessingOutputNumber(
                name=self.RESULT_CODE,
                description=self.tr("Code de résultat. 0 si aucun problème"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_layers = self.parameterAsLayerList(parameters, self.INPUT_LAYERS, context)
        layers = []

        # Load layers from geopackage
        for layer in input_layers:
            filename = layer.dataProvider().dataSourceUri()
            fileinfo = QtCore.QFileInfo(filename)
            if fileinfo.exists() and fileinfo.suffix() == "gpkg":
                gpkg_layers = [
                    gpkg_layer.GetName() for gpkg_layer in ogr.Open(filename)
                ]
                for layer_name in gpkg_layers:
                    layers.append(
                        QgsVectorLayer(f"{filename}|layername={layer_name}", layer_name)
                    )
            else:
                layers.append(layer)

        result_code = self.ResultCode.VALID

        if len(layers) == 0:
            feedback.pushInfo("No input layers defined.")
        else:
            self.add_layers_info_feedback(feedback, layers)
            if not self.check_layers_crs(feedback, layers):
                result_code = result_code | self.ResultCode.CRS_MISMATCH
            if not self.check_layers_name(feedback, layers):
                result_code = result_code | self.ResultCode.INVALID_LAYER_NAME
            if not self.check_file_name(feedback, layers):
                result_code = result_code | self.ResultCode.INVALID_FILE_NAME
            if not self.check_layers_fields(feedback, layers):
                result_code = result_code | self.ResultCode.INVALID_FIELD_NAME
            if not self.check_layers_type(feedback, layers):
                result_code = result_code | self.ResultCode.INVALID_LAYER_TYPE

        return {self.RESULT_CODE: result_code}

    @staticmethod
    def add_layers_info_feedback(
        feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> None:
        """
        Add layers information in feedback

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])
        """
        feedback.pushInfo("Checking layers :")
        for layer in layers:
            feedback.pushInfo(f"- {layer.name()} ({layer.crs().authid()})")

    @staticmethod
    def check_layers_crs(
        feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have the same CRS

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if layers have the same CRS, False otherwise

        """
        res = True
        feedback.pushInfo("Checking layers CRS :")
        ref_crs = None

        for layer in layers:
            if layer.isSpatial():
                layer_crs = layer.crs().authid()
                if not ref_crs:
                    ref_crs = layer.crs().authid()
                    feedback.pushInfo(f"Reference CRS is {ref_crs}")
            else:
                feedback.pushInfo("Layer is not spatial, CRS is not checked.")
                continue

            layer_crs = layer.crs().authid()
            if ref_crs != layer_crs:
                res = False
                feedback.pushWarning(
                    f"- [KO] {layer.name()} : invalid CRS {layer_crs}. Expected {ref_crs}"
                )
        if res:
            feedback.pushInfo("[OK] CRS identical for all input layers")

        return res

    def check_layers_name(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have a valid name

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have valid name, False otherwise

        """
        res = True
        feedback.pushInfo("Checking layers name :")
        for layer in layers:
            layer_name = layer.name()
            if self.has_invalid_character(layer_name):
                res = False
                feedback.pushWarning(
                    f"- [KO] invalid layer name for {layer_name}. "
                    f"Please remove any special character ({self.get_invalid_characters()})"
                )
        if res:
            feedback.pushInfo("[OK] valid layer name for all input layers")

        return res

    def check_file_name(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have a valid file name

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have valid name, False otherwise

        """
        res = True
        feedback.pushInfo("Checking file names :")
        for layer in layers:
            file_name = layer.dataProvider().dataSourceUri()
            if self.has_invalid_character(file_name):
                res = False
                feedback.pushWarning(
                    f"- [KO] invalid file name for {file_name}. "
                    f"Please remove any special character ({self.get_invalid_characters()})"
                )
        if res:
            feedback.pushInfo("[OK] valid file name for all input layers")

        return res

    def check_layers_fields(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have valid fields name

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have valid fields name, False otherwise

        """
        res = True
        feedback.pushInfo("Checking layers fields name :")
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                if not self.check_layer_fields(feedback, layer):
                    res = False
        if res:
            feedback.pushInfo("[OK] valid layer fields name for all input layers")

        return res

    def check_layer_fields(
        self, feedback: QgsProcessingFeedback, layer: QgsVectorLayer
    ) -> bool:
        """
        Check that layer have valid fields name

        Args:
            feedback: QgsProcessingFeedback
            layer: QgsVectorLayer

        Returns: True if layer have valid fields name, False otherwise

        """
        res = True
        layer_name = layer.name()
        for field in layer.fields():
            field_name = field.name()
            if self.has_invalid_character(field_name):
                res = False
                feedback.pushWarning(
                    f"- [KO] invalid layer field name {field_name} for {layer_name}. "
                    f"Please remove any special character ({self.get_invalid_characters()})"
                )
        return res

    @staticmethod
    def check_layers_type(
        feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have valid fields name

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have valid name, False otherwise

        """
        res = True
        feedback.pushInfo("Checking layers fields name :")
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                res = False
                feedback.pushWarning(
                    f"- [KO] invalid layer type for {layer.name()}. Only QgsVectorLayer are supported."
                )

        if res:
            feedback.pushInfo("[OK] valid layer fields name for all input layers")

        return res

    def has_invalid_character(self, test_str: str) -> bool:
        """
        Check a invalid character is present in test string

        Args:
            test_str: (str) test string

        Returns: True if an invalid character is present in test string, False otherwise

        """
        string_check = re.compile(f"[{self.get_invalid_characters()}]")
        return string_check.search(test_str) is not None

    @staticmethod
    def get_invalid_characters() -> str:
        """
        Return invalid characters

        Returns: invalid characters for XML use : <>\"&'

        """
        return "<>\"&'"
