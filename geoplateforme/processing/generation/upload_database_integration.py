from time import sleep

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterMatrix,
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


class UploadDatabaseIntegrationAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    UPLOAD = "UPLOAD"
    STORED_DATA_NAME = "STORED_DATA_NAME"
    TAGS = "TAGS"
    WAIT_FOR_INTEGRATION = "WAIT_FOR_INTEGRATION"

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
        return UploadDatabaseIntegrationAlgorithm()

    def name(self):
        return "upload_database_integration"

    def displayName(self):
        return self.tr("Intégration d'une livraison en base de données vectorielle")

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
                name=self.UPLOAD,
                description=self.tr("Identifiant de la livraison"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.STORED_DATA_NAME,
                description=self.tr("Nom de la base de données vectorielle"),
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
                self.WAIT_FOR_INTEGRATION,
                self.tr("Attendre la fin de l'intégration ?"),
                defaultValue=False,
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.CREATED_STORED_DATA_ID,
                description=self.tr("Identifiant de la base de données créée."),
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
        upload = self.parameterAsString(parameters, self.UPLOAD, context)

        tag_data = self.parameterAsMatrix(parameters, self.TAGS, context)
        tags = tags_from_qgs_parameter_matrix_string(tag_data)

        wait_for_integration = self.parameterAsBool(
            parameters, self.WAIT_FOR_INTEGRATION, context
        )

        try:
            stored_data_manager = StoredDataRequestManager()
            processing_manager = ProcessingRequestManager()

            # Get processing for database integration
            processing = processing_manager.get_processing(
                datastore,
                PlgOptionsManager.get_plg_settings().vector_db_generation_processing_names,
            )

            # Create execution
            data_map = {
                "processing": processing._id,
                "inputs": {"upload": [upload]},
                "output": {"stored_data": {"name": stored_data_name}},
                "parameters": {},
            }
            res = processing_manager.create_processing_execution(
                datastore_id=datastore, input_map=data_map
            )
            stored_data_val = res["output"]["stored_data"]
            exec_id = res["_id"]

            # Get created stored_data id
            stored_data_id = stored_data_val["_id"]

            # Update feedback if vector db id attribute present
            if hasattr(feedback, "created_vector_db_id"):
                feedback.created_vector_db_id = stored_data_id

            # Update stored data tags
            tags["upload_id"] = upload
            tags["proc_int_id"] = exec_id

            stored_data_manager.add_tags(
                datastore_id=datastore,
                stored_data_id=stored_data_val["_id"],
                tags=tags,
            )

            # Update tags for upload
            upload_tags = {
                "vectordb_id": stored_data_id,
                "proc_int_id": exec_id,
                "integration_progress": '{"send_files_api":"successful","wait_checks":"successful","integration_processing":"in_progress"}',
                "integration_current_step": "2",
            }

            self._add_upload_tag(
                datastore_id=datastore,
                upload_id=upload,
                tags=upload_tags,
            )

            # Launch execution
            processing_manager.launch_execution(datastore_id=datastore, exec_id=exec_id)

            if wait_for_integration:
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
