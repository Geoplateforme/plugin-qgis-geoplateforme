# standard
from typing import Any, Dict, List, Optional

# PyQGIS
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFile,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication

from geoplateforme.processing.upload.upload_from_files import GpfUploadFromFileAlgorithm

# plugin
from geoplateforme.processing.utils import (
    get_shapefile_associated_files,
    get_short_string,
    get_user_manual_url,
)


class GpfUploadFromLayersAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    NAME = "NAME"
    DESCRIPTION = "DESCRIPTION"
    LAYERS = "LAYERS"
    FILES = "FILES"
    SRS = "SRS"
    TAGS = "TAGS"
    WAIT_FOR_CLOSE = "WAIT_FOR_CLOSE"

    CREATED_UPLOAD_ID = "CREATED_UPLOAD_ID"

    SUPPORTED_SOURCE_TYPES = ["GPKG", "ESRI Shapefile", "GeoJSON"]

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return GpfUploadFromLayersAlgorithm()

    def name(self):
        return "upload_from_layer"

    def displayName(self):
        return self.tr("Création livraison depuis des couches vectorielles")

    def group(self):
        return self.tr("Livraison")

    def groupId(self):
        return "upload"

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def layer_parameter(self) -> QgsProcessingParameterMultipleLayers:
        """Parameter for layer definition

        :return: parameter
        :rtype: QgsProcessingParameterMultipleLayers
        """
        return QgsProcessingParameterMultipleLayers(
            name=self.LAYERS,
            description=self.tr("Couches vectorielles à livrer"),
            layerType=Qgis.ProcessingSourceType.VectorAnyGeometry,
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                name=self.DATASTORE,
                description=self.tr("Identifiant de l'entrepôt"),
            )
        )

        self.addParameter(self.layer_parameter())

        self.addParameter(
            QgsProcessingParameterFile(
                name=self.FILES,
                description=self.tr(
                    "Fichiers additionnels à importer (séparés par ; pour fichiers multiples)"
                ),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.NAME,
                description=self.tr("Nom de la livraison"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.DESCRIPTION,
                description=self.tr("Description de la livraison"),
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(self.SRS, self.tr("Système de coordonnées"))
        )

        self.addParameter(
            QgsProcessingParameterMatrix(
                name=self.TAGS,
                description=self.tr("Tags"),
                headers=[self.tr("Tag"), self.tr("Valeur")],
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.WAIT_FOR_CLOSE,
                self.tr("Attendre la fermeture de la livraison ?"),
                defaultValue=False,
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.CREATED_UPLOAD_ID,
                description=self.tr("Identifiant de la livraison créée"),
            )
        )

    def export_layer_as_temporary_gpkg(
        self, layer: QgsVectorLayer, context: QgsProcessingContext
    ) -> str:
        """Export layer in a temporary GPKG

        :param layer: layer to export
        :type layer: QgsVectorLayer
        :param context: processing context
        :type context: QgsProcessingContext
        :raises QgsProcessingException: error during layer export
        :return: path to temporary GPKG
        :rtype: str
        """
        temp_output = QgsProcessingParameterVectorDestination(
            name=layer.name()
        ).generateTemporaryDestination()

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = layer.name()
        options.actionOnExistingFile = (
            QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
        )

        error, error_str, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, temp_output, context.transformContext(), options
        )

        if error != QgsVectorFileWriter.WriterError.NoError:
            raise QgsProcessingException(
                self.tr(
                    "Erreur lors l'export de la couche {} dans une couche temporaire GPKG {} : {}"
                ).format(layer.name(), temp_output, error_str)
            )
        return temp_output

    def processAlgorithm(
        self,
        parameters: Dict[str, Any],
        context: QgsProcessingContext,
        feedback: Optional[QgsProcessingFeedback],
    ) -> Dict[str, Any]:
        """Runs the algorithm using the specified parameters.

        :param parameters: algorithm parameters
        :type parameters: Dict[str, Any]
        :param context: processing context
        :type context: QgsProcessingContext
        :param feedback: processing feedback
        :type feedback: Optional[QgsProcessingFeedback]
        :raises QgsProcessingException: Multiple crs for input layers
        :raises QgsProcessingException: Error in upload creation
        :return: algorithm results
        :rtype: Dict[str, Any]
        """
        name = self.parameterAsString(parameters, self.NAME, context)
        description = self.parameterAsString(parameters, self.DESCRIPTION, context)
        datastore = self.parameterAsString(parameters, self.DATASTORE, context)
        tags = self.parameterAsMatrix(parameters, self.TAGS, context)
        wait_for_close = self.parameterAsBool(parameters, self.WAIT_FOR_CLOSE, context)

        layers: List[QgsVectorLayer] = self.parameterAsLayerList(
            parameters, self.LAYERS, context
        )

        # define CRS from input layers
        srs: QgsCoordinateReferenceSystem = self.parameterAsCrs(
            parameters, self.SRS, context
        )

        # Check CRS for all input layers
        for layer in layers:
            layer_crs = layer.dataProvider().crs()
            if layer_crs != srs:
                raise QgsProcessingException(
                    self.tr(
                        "Toutes les couches doivent avoir le même système de coordonnées pour la livraison."
                    )
                )

        # define files from input files
        files = []
        file_str = self.parameterAsString(parameters, self.FILES, context)
        if file_str:
            files = file_str.split(";")

        added_files = []
        for file in files:
            layer = QgsVectorLayer(file)
            if layer.isValid():
                if layer.storageType() == "ESRI Shapefile":
                    source = layer.source()
                    added_files.extend(get_shapefile_associated_files(source))
        files.extend(added_files)

        # define files from input layers
        for layer in layers:
            storage_type = layer.storageType()
            if storage_type not in self.SUPPORTED_SOURCE_TYPES:
                feedback.pushInfo(
                    self.tr(
                        "Les fichiers de type {} ne sont pas supportées (format supportés {}). Un export en GPKG est effectué."
                    ).format(storage_type, self.SUPPORTED_SOURCE_TYPES)
                )
                files.append(self.export_layer_as_temporary_gpkg(layer, context))
            elif storage_type == "GPKG":
                feedback.pushInfo(
                    self.tr(
                        "Les fichiers GPKG peuvent contenir plusieurs couches. Un export dans un GPKG temporaire est effectué pour ne livrer que les données de la couche."
                    )
                )
                files.append(self.export_layer_as_temporary_gpkg(layer, context))

            elif storage_type == "ESRI Shapefile":
                source = layer.source()
                files.append(source)
                files.extend(get_shapefile_associated_files(source))
            elif storage_type == "GeoJSON":
                files.append(layer.source())

        algo_str = f"geoplateforme:{GpfUploadFromFileAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)
        params = {
            GpfUploadFromFileAlgorithm.DATASTORE: datastore,
            GpfUploadFromFileAlgorithm.NAME: name,
            GpfUploadFromFileAlgorithm.DESCRIPTION: description,
            GpfUploadFromFileAlgorithm.SRS: srs,
            GpfUploadFromFileAlgorithm.FILES: ";".join(files),
            GpfUploadFromFileAlgorithm.TAGS: tags,
            GpfUploadFromFileAlgorithm.WAIT_FOR_CLOSE: wait_for_close,
        }

        results, successful = alg.run(params, context, feedback)
        if successful:
            created_upload_id = results[GpfUploadFromFileAlgorithm.CREATED_UPLOAD_ID]
        else:
            raise QgsProcessingException(self.tr("Upload creation failed"))

        return {self.CREATED_UPLOAD_ID: created_upload_id}
