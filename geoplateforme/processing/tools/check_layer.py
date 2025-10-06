import re
from enum import IntFlag
from typing import List

from osgeo import ogr
from qgis import processing
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
        INVALID_GEOMETRY = 32
        NO_FEATURES = 64

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
            feedback.pushInfo(self.tr("No input layers defined."))
        else:
            self.add_layers_info_feedback(feedback, layers)
            if not self.check_layers_crs(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.CRS_MISMATCH}
            if not self.check_layers_name(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.INVALID_LAYER_NAME}
            if not self.check_file_name(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.INVALID_FILE_NAME}
            if not self.check_layers_fields(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.INVALID_FIELD_NAME}
            if not self.check_layers_type(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.INVALID_LAYER_TYPE}
            if not self.check_layers_geometry(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.INVALID_GEOMETRY}
            if not self.check_layers_nb_features(feedback, layers):
                return {self.RESULT_CODE: self.ResultCode.NO_FEATURES}

        return {self.RESULT_CODE: result_code}

    def add_layers_info_feedback(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> None:
        """
        Add layers information in feedback

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])
        """
        feedback.pushInfo(self.tr("Checking layers :"))
        for layer in layers:
            feedback.pushInfo(f"- {layer.name()} ({layer.crs().authid()})")

    def check_layers_crs(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have the same CRS

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if layers have the same CRS, False otherwise

        """
        res = True
        feedback.pushInfo(self.tr("Checking layers CRS :"))
        ref_crs = None

        for layer in layers:
            if layer.isSpatial():
                layer_crs = layer.crs().authid()
                if not ref_crs:
                    ref_crs = layer.crs().authid()
                    feedback.pushInfo(self.tr("Reference CRS is {}".format(ref_crs)))
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
                    self.tr(
                        "- [KO] invalid layer name for {}. Please remove any special character ({})"
                    ).format(layer_name, self.get_invalid_characters())
                )
        if res:
            feedback.pushInfo(self.tr("[OK] valid layer name for all input layers"))

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
        feedback.pushInfo(self.tr("Checking file names :"))
        for layer in layers:
            if layer.providerType() == "memory":
                continue
            file_name = layer.dataProvider().dataSourceUri()
            if self.has_invalid_character(file_name):
                res = False
                feedback.pushWarning(
                    self.tr(
                        "- [KO] invalid file name for {}. Please remove any special character ({})"
                    ).format(file_name, self.get_invalid_characters())
                )
        if res:
            feedback.pushInfo(self.tr("[OK] valid file name for all input layers"))

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
        feedback.pushInfo(self.tr("Checking layers fields name :"))
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                if not self.check_layer_fields(feedback, layer):
                    res = False
        if res:
            feedback.pushInfo(
                self.tr("[OK] valid layer fields name for all input layers")
            )

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
                    self.tr(
                        "- [KO] invalid layer field name {} for {}. Please remove any special character ({})"
                    ).format(field_name, layer_name, self.get_invalid_characters())
                )
        return res

    def check_layers_type(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have valid type

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have valid type, False otherwise

        """
        res = True
        feedback.pushInfo("Checking layers type :")
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                res = False
                feedback.pushWarning(
                    self.tr(
                        "- [KO] invalid layer type for {}. Only QgsVectorLayer are supported."
                    ).format(layer.name())
                )

        if res:
            feedback.pushInfo(self.tr("[OK] valid layer type for all input layers"))

        return res

    def check_layers_geometry(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have valid geometry

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have valid geometry, False otherwise

        """

        res = True
        feedback.pushInfo(self.tr("Checking layers geometry :"))
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                continue
            parameters = {
                "INPUT_LAYER": layer,
                "METHOD": 1,
                "IGNORE_RING_SELF_INTERSECTION": False,
                "VALID_OUTPUT": "TEMPORARY_OUTPUT",
                "INVALID_OUTPUT": "TEMPORARY_OUTPUT",
                "ERROR_OUTPUT": "TEMPORARY_OUTPUT",
            }
            result = processing.run("qgis:checkvalidity", parameters)
            error_count = result["ERROR_COUNT"]
            if error_count != 0:
                res = False
                feedback.pushWarning(
                    self.tr("- [KO] geometries with errors for {}.").format(
                        layer.name()
                    )
                )
            invalid_count = result["INVALID_COUNT"]
            if invalid_count != 0:
                res = False
                feedback.pushWarning(
                    self.tr("- [KO] invalid geometries for {}.").format(layer.name())
                )
        if res:
            feedback.pushInfo(self.tr("[OK] valid layer geometry for all input layers"))

        return res

    def check_layers_nb_features(
        self, feedback: QgsProcessingFeedback, layers: List[QgsMapLayer]
    ) -> bool:
        """
        Check that layers have valid bbox

        Args:
            feedback: QgsProcessingFeedback
            layers: List[QgsMapLayer])

        Returns: True if all layers have bbox, False otherwise

        """
        res = True
        feedback.pushInfo(self.tr("Checking layers number of features :"))
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer):
                continue
            if layer.featureCount() == 0:
                res = False
                feedback.pushWarning(
                    self.tr(
                        "- [KO] no feature for {}. At least one feature must be available."
                    ).format(layer.name())
                )

        if res:
            feedback.pushInfo(self.tr("[OK] features availables for all input layers"))

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
