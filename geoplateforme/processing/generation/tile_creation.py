import json
from time import sleep

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterExtent,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# plugin
from geoplateforme.api.custom_exceptions import (
    AddTagException,
    CreateProcessingException,
    LaunchExecutionException,
    ReadStoredDataException,
    UnavailableProcessingException,
    UnavailableStoredData,
)
from geoplateforme.api.processing import ProcessingRequestManager
from geoplateforme.api.stored_data import StoredDataRequestManager, StoredDataStatus
from geoplateforme.processing.utils import (
    get_short_string,
    get_user_manual_url,
    tags_from_qgs_parameter_matrix_string,
)
from geoplateforme.toolbelt import PlgOptionsManager


class TileCreationAlgorithm(QgsProcessingAlgorithm):
    INPUT_JSON = "INPUT_JSON"

    DATASTORE = "DATASTORE"
    VECTOR_DB_STORED_DATA_ID = "VECTOR_DB_STORED_DATA_ID"
    STORED_DATA_NAME = "STORED_DATA_NAME"
    TIPPECANOE_OPTIONS = "TIPPECANOE_OPTIONS"
    COMPOSITION = "COMPOSITION"
    BOTTOM_LEVEL = "BOTTOM_LEVEL"
    TOP_LEVEL = "TOP_LEVEL"
    BBOX = "BBOX"
    TAGS = "TAGS"
    WAIT_FOR_GENERATION = "WAIT_FOR_GENERATION"

    TABLE = "table"
    ATTRIBUTES = "attributes"
    DATASET_NAME = "dataset_name"
    COMPOSITION_BOTTOM_LEVEL = "bottom_level"
    COMPOSITION_TOP_LEVEL = "top_level"

    PROCESSING_EXEC_ID = "PROCESSING_EXEC_ID"
    CREATED_STORED_DATA_ID = "CREATED_STORED_DATA_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return TileCreationAlgorithm()

    def name(self):
        return "tile_creation"

    def displayName(self):
        return self.tr("Génération de tuiles vectorielles")

    def group(self):
        return self.tr("Génération données")

    def groupId(self):
        return "generation"

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
                name=self.VECTOR_DB_STORED_DATA_ID,
                description=self.tr("Identifiant de la base de données vectorielles"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.STORED_DATA_NAME,
                description=self.tr("Nom des tuiles en sortie"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.TIPPECANOE_OPTIONS,
                description=self.tr("Options tippecanoe"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.COMPOSITION,
                description=self.tr("JSON pour la composition"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.BOTTOM_LEVEL,
                description=self.tr("Niveau bas de la pyramide"),
                minValue=1,
                maxValue=21,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.TOP_LEVEL,
                description=self.tr("Niveau haut de la pyramide"),
                minValue=1,
                maxValue=21,
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(
                name=self.BBOX,
                description=self.tr("Zone de moissonnage"),
                optional=True,
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

        self.addOutput(
            QgsProcessingOutputString(
                name=self.CREATED_STORED_DATA_ID,
                description=self.tr("Identifiant des tuiles vectorielles créés."),
            )
        )
        self.addOutput(
            QgsProcessingOutputString(
                name=self.PROCESSING_EXEC_ID,
                description=self.tr("Identifiant de l'exécution du traitement."),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        stored_data_name = self.parameterAsString(
            parameters, self.STORED_DATA_NAME, context
        )

        datastore = self.parameterAsString(parameters, self.DATASTORE, context)
        vector_db_stored_data_id = self.parameterAsString(
            parameters, self.VECTOR_DB_STORED_DATA_ID, context
        )

        tag_data = self.parameterAsMatrix(parameters, self.TAGS, context)
        tags = tags_from_qgs_parameter_matrix_string(tag_data)

        wait_for_generation = self.parameterAsBool(
            parameters, self.WAIT_FOR_GENERATION, context
        )

        tippecanoe_options = self.parameterAsString(
            parameters, self.TIPPECANOE_OPTIONS, context
        )

        composition_str = self.parameterAsString(parameters, self.COMPOSITION, context)
        composition: dict[str, str] | None = None
        if composition_str:
            composition = json.loads(composition_str)
            self._check_composition(composition)

        bottom_level = self.parameterAsInt(parameters, self.BOTTOM_LEVEL, context)
        top_level = self.parameterAsInt(parameters, self.TOP_LEVEL, context)

        try:
            stored_data_manager = StoredDataRequestManager()
            processing_manager = ProcessingRequestManager()

            vector_db_stored_data = stored_data_manager.get_stored_data(
                datastore, vector_db_stored_data_id
            )

            # Get processing for tile creation
            processing = processing_manager.get_processing(
                datastore,
                PlgOptionsManager.get_plg_settings().vector_tile_generation_processing_names,
            )
            # Execution parameters
            exec_params = {
                "bottom_level": str(bottom_level),
                "top_level": str(top_level),
            }

            if tippecanoe_options:
                exec_params["tippecanoe_options"] = tippecanoe_options

            bbox_used = False

            # TODO : need to update BBOX parameter to define area as wkt in EPSG:4326
            # if self.BBOX in data:
            #    exec_params[self.BBOX] = data[self.BBOX]
            #    bbox_used = True

            if composition is not None:
                exec_params["composition"] = composition

            # Create execution
            data_map = {
                "processing": processing._id,
                "inputs": {"stored_data": [vector_db_stored_data_id]},
                "output": {"stored_data": {"name": stored_data_name}},
                "parameters": exec_params,
            }
            res = processing_manager.create_processing_execution(
                datastore_id=datastore, input_map=data_map
            )
            stored_data_val = res["output"]["stored_data"]
            exec_id = res["_id"]

            # Get created stored_data id
            stored_data_id = stored_data_val["_id"]

            # Update feedback if attribute is present
            if hasattr(feedback, "created_pyramid_id"):
                feedback.created_pyramid_id = stored_data_id

            # Update stored data tags
            tags["upload_id"] = vector_db_stored_data.tags.get("upload_id", "")
            tags["proc_int_id"] = vector_db_stored_data.tags.get("proc_int_id", "")
            tags["vectordb_id"] = vector_db_stored_data._id
            tags["pyramid_id"] = stored_data_id
            tags["proc_pyr_creat_id"] = exec_id

            if bbox_used:
                tags["is_sample"] = "true"

            stored_data_manager.add_tags(
                datastore_id=datastore,
                stored_data_id=stored_data_val["_id"],
                tags=tags,
            )

            # Add tag to vector db
            vector_db_tag = {
                "pyramid_id": stored_data_id,
            }
            stored_data_manager.add_tags(
                datastore_id=datastore,
                stored_data_id=vector_db_stored_data._id,
                tags=vector_db_tag,
            )

            # Launch execution
            processing_manager.launch_execution(datastore_id=datastore, exec_id=exec_id)

            if wait_for_generation:
                # Wait for tile creation
                self._wait_tile_creation(datastore, stored_data_id, feedback)

        except UnavailableStoredData as exc:
            raise QgsProcessingException(
                f"Can't retrieve vector db datastore for tile creation : {exc}"
            )
        except UnavailableProcessingException as exc:
            raise QgsProcessingException(
                f"Can't retrieve processing for tile creation : {exc}"
            )
        except CreateProcessingException as exc:
            raise QgsProcessingException(
                f"Can't create processing execution for tile creation : {exc}"
            )
        except LaunchExecutionException as exc:
            raise QgsProcessingException(
                f"Can't launch execution for tile creation : {exc}"
            )
        except AddTagException as exc:
            raise QgsProcessingException(
                f"Can't add tags to stored data for tile creation : {exc}"
            )

        return {
            self.CREATED_STORED_DATA_ID: stored_data_id,
            self.PROCESSING_EXEC_ID: exec_id,
        }

    def _check_composition(self, data) -> None:
        """
        Check composition data, raises QgsProcessingException in case of errors

        Args:
            data: input composition data
        """
        if not isinstance(data, list):
            raise QgsProcessingException(
                f"Invalid {self.COMPOSITION} key in input json.  Expected list, not {type(data)}"
            )

        mandatory_keys = [self.TABLE, self.ATTRIBUTES]
        for compo in data:
            missing_keys = [key for key in mandatory_keys if key not in compo]

            if missing_keys:
                raise QgsProcessingException(
                    f"Missing {', '.join(missing_keys)} keys for {self.COMPOSITION} item in input json."
                )

    def _wait_tile_creation(
        self,
        datastore: str,
        pyramid_stored_data_id: str,
        feedback: QgsProcessingFeedback,
    ) -> None:
        """
        Wait until tile creation is done (GENERATED status) or throw exception if status is UNSTABLE

        Args:
            datastore: (str) datastore id
            pyramid_stored_data_id: (str) pyramid stored data id
            feedback: (QgsProcessingFeedback) : feedback to cancel wait
        """
        try:
            manager = StoredDataRequestManager()
            stored_data = manager.get_stored_data(
                datastore_id=datastore, stored_data_id=pyramid_stored_data_id
            )
            status = StoredDataStatus(stored_data.status)
            while (
                status != StoredDataStatus.GENERATED
                and status != StoredDataStatus.UNSTABLE
            ):
                stored_data = manager.get_stored_data(
                    datastore_id=datastore, stored_data_id=pyramid_stored_data_id
                )
                status = StoredDataStatus(stored_data.status)
                sleep(PlgOptionsManager.get_plg_settings().status_check_sleep)

                if feedback.isCanceled():
                    return

            if status == StoredDataStatus.UNSTABLE:
                raise QgsProcessingException(
                    self.tr(
                        "Tile creation failed. Check report in dashboard for more details."
                    )
                )

        except ReadStoredDataException as exc:
            raise QgsProcessingException(f"Stored data read failed : {exc}")
