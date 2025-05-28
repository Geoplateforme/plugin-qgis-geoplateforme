from time import sleep

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

from geoplateforme.api.custom_exceptions import (
    AddTagException,
    CreateProcessingException,
    LaunchExecutionException,
    ReadStoredDataException,
    UnavailableProcessingException,
)
from geoplateforme.api.processing import ProcessingRequestManager
from geoplateforme.api.stored_data import StoredDataRequestManager, StoredDataStatus
from geoplateforme.api.upload import UploadRequestManager
from geoplateforme.processing.utils import (
    get_short_string,
    get_user_manual_url,
    tags_from_qgs_parameter_matrix_string,
)
from geoplateforme.toolbelt import PlgOptionsManager


class RasterTilesFromWmsVectorAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    STORED_DATA_NAME = "STORED_DATA_NAME"

    HARVEST_LAYERS = "HARVEST_LAYERS"
    HARVEST_LEVELS = "HARVEST_LEVELS"
    HARVEST_EXTRA = "HARVEST_EXTRA"
    HARVEST_FORMAT = "HARVEST_FORMAT"
    HARVEST_URL = "HARVEST_URL"
    HARVEST_DIMENSION = "HARVEST_DIMENSION"
    HARVEST_AREA = "HARVEST_AREA"
    PARALLELIZATION = "PARALLELIZATION"
    BOTTOM = "BOTTOM"
    TOP = "TOP"
    COMPRESSION = "COMPRESSION"
    NODATA = "NODATA"
    HEIGHT = "HEIGHT"
    WIDTH = "WIDTH"
    TMS = "TMS"
    SAMPLE_FORMAT = "SAMPLE_FORMAT"
    SAMPLES_PER_PIXEL = "SAMPLES_PER_PIXEL"
    TAGS = "TAGS"
    WAIT_FOR_GENERATION = "WAIT_FOR_GENERATION"

    PROCESSING_EXEC_ID = "PROCESSING_EXEC_ID"
    CREATED_STORED_DATA_ID = "CREATED_STORED_DATA_ID"

    COMPRESSION_ENUM = ["jpg", "png", "none", "png", "zip", "jpg90"]
    SAMPLE_FORMAT_ENUM = ["UINT8", "FLOAT32"]

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return RasterTilesFromWmsVectorAlgorithm()

    def name(self):
        return "raster_tiles_from_wms_vector"

    def displayName(self):
        return self.tr("Génération tuiles raster depuis un service WMS-Vecteur")

    def group(self):
        return self.tr("")

    def groupId(self):
        return ""

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                name=self.DATASTORE,
                description=self.tr("Identifiant de l'entrepôt"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.STORED_DATA_NAME,
                description=self.tr("Nom des tuiles raster"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.HARVEST_LAYERS,
                description=self.tr(
                    "Nom des couches à moissonner. Valeurs multiples séparées par des virgules."
                ),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.HARVEST_LEVELS,
                description=self.tr(
                    "Niveau de moissonage. Valeurs multiples séparées par des virgules."
                ),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.HARVEST_EXTRA,
                description=self.tr("Paramètres de requêtes GetMap additionnels."),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.HARVEST_FORMAT,
                description=self.tr("Format des images téléchargées."),
                defaultValue="image/jpeg",
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.HARVEST_URL,
                description=self.tr("URL du service WMS."),
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(
                name=self.HARVEST_AREA,
                description=self.tr("Zone moissonnage."),
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.BOTTOM,
                description=self.tr("Le niveau du bas de la pyramide en sortie."),
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.TOP,
                description=self.tr("Le niveau du haut de la pyramide en sortie."),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.COMPRESSION,
                description=self.tr("Compression des données en sortie."),
                options=self.COMPRESSION_ENUM,
                defaultValue="jpg",
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.HEIGHT,
                description=self.tr("Le nombre de tuile par dalle en hauteur."),
                defaultValue=16,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.WIDTH,
                description=self.tr("Le nombre de tuile par dalle en largeur."),
                defaultValue=16,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.TMS,
                description=self.tr(
                    "Identifiant du quadrillage à utiliser (Tile Matrix Set)"
                ),
                defaultValue="PM",
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.SAMPLE_FORMAT,
                description=self.tr("Format des canaux dans les dalles en sortie."),
                options=self.SAMPLE_FORMAT_ENUM,
                defaultValue="UINT8",
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.SAMPLES_PER_PIXEL,
                description=self.tr("Nombre de canaux dans les dalles en sortie."),
                minValue=1,
                maxValue=4,
                defaultValue=3,
            )
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
                self.WAIT_FOR_GENERATION,
                self.tr("Attendre la fin de la génération ?"),
                defaultValue=False,
            )
        )

        # TODO : gestion dimension : HARVEST_DIMENSION = "HARVEST_DIMENSION"
        # TODO : gestion parallélisation PARALLELIZATION = "PARALLELIZATION"
        # TODO : gestion nodata NODATA = "NODATA"

    def processAlgorithm(self, parameters, context, feedback):
        stored_data_name = self.parameterAsString(
            parameters, self.STORED_DATA_NAME, context
        )
        datastore = self.parameterAsString(parameters, self.DATASTORE, context)

        harvest_level_str = self.parameterAsString(
            parameters, self.HARVEST_LEVELS, context
        )
        harvest_level = harvest_level_str.split(",")

        bottom = self.parameterAsInt(parameters, self.BOTTOM, context)
        harvest_layers_str = self.parameterAsString(
            parameters, self.HARVEST_LAYERS, context
        )
        width = self.parameterAsInt(parameters, self.WIDTH, context)
        height = self.parameterAsInt(parameters, self.HEIGHT, context)

        harvest_url = self.parameterAsString(
            parameters,
            self.HARVEST_URL,
            context,
        )
        harvest_area = self.parameterAsExtentGeometry(
            parameters,
            self.HARVEST_AREA,
            context,
            crs=QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        compression = self.parameterAsEnumString(parameters, self.COMPRESSION, context)
        sample_format = self.parameterAsEnumString(
            parameters, self.SAMPLE_FORMAT, context
        )
        samples_per_pixel = self.parameterAsInt(
            parameters, self.SAMPLES_PER_PIXEL, context
        )

        tag_data = self.parameterAsMatrix(parameters, self.TAGS, context)
        tags = tags_from_qgs_parameter_matrix_string(tag_data)

        wait_for_generation = self.parameterAsBool(
            parameters, self.WAIT_FOR_GENERATION, context
        )

        try:
            stored_data_manager = StoredDataRequestManager()
            processing_manager = ProcessingRequestManager()

            # Get processing for database integration
            processing = processing_manager.get_processing_by_id(
                datastore,
                PlgOptionsManager.get_plg_settings().raster_tiles_from_wms_vector_processing_ids,
            )

            parameters = {
                "harvest_levels": harvest_level,
                "bottom": str(bottom),
                "harvest_layers": harvest_layers_str,
                "parallelization": 1,
                "harvest_area": harvest_area.asWkt(),
                "width": width,
                "harvest_format": "image/jpeg",
                "harvest_url": harvest_url,
                "tms": "PM",
                "compression": compression,
                "sampleformat": sample_format,
                "samplesperpixel": samples_per_pixel,
                "height": height,
            }

            # Create execution
            data_map = {
                "processing": processing._id,
                "inputs": {},
                "output": {"stored_data": {"name": stored_data_name}},
                "parameters": parameters,
            }
            res = processing_manager.create_processing_execution(
                datastore_id=datastore, input_map=data_map
            )
            stored_data_val = res["output"]["stored_data"]
            exec_id = res["_id"]

            # Get created stored_data id
            stored_data_id = stored_data_val["_id"]

            # Update stored data tags
            # TODO there is no stored data in input. We must get info from configuration ?
            # tags["upload_id"] = vector_db_stored_data.tags.get("upload_id", "")
            # tags["proc_int_id"] = vector_db_stored_data.tags.get("proc_int_id", "")
            # tags["vectordb_id"] = vector_db_stored_data._id
            tags["proc_pyr_creat_id"] = exec_id

            stored_data_manager.add_tags(
                datastore_id=datastore,
                stored_data_id=stored_data_val["_id"],
                tags=tags,
            )

            # Launch execution
            processing_manager.launch_execution(datastore_id=datastore, exec_id=exec_id)

            if wait_for_generation:
                # Wait for database integration
                self._wait_database_integration(datastore, stored_data_id, feedback)

        except UnavailableProcessingException as exc:
            raise QgsProcessingException(
                f"Can't retrieve processing for database integration : {exc}"
            )
        except CreateProcessingException as exc:
            raise QgsProcessingException(
                f"Can't create processing execution for database integration : {exc}"
            )
        except LaunchExecutionException as exc:
            raise QgsProcessingException(
                f"Can't launch execution for database integration : {exc}"
            )
        except AddTagException as exc:
            raise QgsProcessingException(
                f"Can't add tags to stored data for database integration : {exc}"
            )

        return {
            self.CREATED_STORED_DATA_ID: stored_data_id,
            self.PROCESSING_EXEC_ID: exec_id,
        }

    def _add_upload_tag(
        self, datastore_id: str, upload_id: str, tags: dict[str, str]
    ) -> None:
        """Add tags to an upload

        :param datastore_id: datastore id
        :type datastore_id: str
        :param upload_id: upload id
        :type upload_id: str
        :param tags: tags
        :type tags: dict[str, str]
        :raises QgsProcessingException: propagate error in case of tag add exception
        """
        try:
            # Update stored data tags
            manager = UploadRequestManager()
            manager.add_tags(
                datastore_id=datastore_id,
                upload_id=upload_id,
                tags=tags,
            )
        except AddTagException as exc:
            raise QgsProcessingException(
                self.tr("Upload tag add failed : {0}").format(exc)
            )

    def _wait_database_integration(
        self,
        datastore: str,
        vector_db_stored_data_id: str,
        feedback: QgsProcessingFeedback,
    ) -> None:
        """
        Wait until database integration is done (GENERATED status) or throw exception if status is UNSTABLE

        Args:
            datastore: (str) datastore id
            vector_db_stored_data_id: (str) vector db stored data id
            feedback: (QgsProcessingFeedback) : feedback to cancel wait
        """
        try:
            manager = StoredDataRequestManager()
            stored_data = manager.get_stored_data(
                datastore_id=datastore, stored_data_id=vector_db_stored_data_id
            )
            status = stored_data.status
            while (
                status != StoredDataStatus.GENERATED
                and status != StoredDataStatus.UNSTABLE
            ):
                stored_data = manager.get_stored_data(
                    datastore_id=datastore, stored_data_id=vector_db_stored_data_id
                )
                status = stored_data.status
                sleep(PlgOptionsManager.get_plg_settings().status_check_sleep)

                if feedback.isCanceled():
                    return

            if status == StoredDataStatus.UNSTABLE:
                raise QgsProcessingException(
                    self.tr(
                        "Database integration failed. Check report in dashboard for more details."
                    )
                )

        except ReadStoredDataException as exc:
            raise QgsProcessingException(f"Stored data read failed : {exc}")
