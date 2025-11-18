# standard
from pathlib import Path
from time import sleep
from typing import Any, Dict, Optional

# PyQGIS
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFile,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# plugin
from geoplateforme.api.custom_exceptions import (
    AddTagException,
    FileUploadException,
    UnavailableUploadException,
    UploadClosingException,
    UploadCreationException,
)
from geoplateforme.api.upload import UploadRequestManager, UploadStatus
from geoplateforme.processing.utils import (
    get_short_string,
    get_user_manual_url,
    tags_from_qgs_parameter_matrix_string,
)
from geoplateforme.toolbelt import PlgOptionsManager


class GpfUploadFromFileAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    NAME = "NAME"
    DESCRIPTION = "DESCRIPTION"
    FILES = "FILES"
    SRS = "SRS"
    TAGS = "TAGS"
    WAIT_FOR_CLOSE = "WAIT_FOR_CLOSE"

    CREATED_UPLOAD_ID = "CREATED_UPLOAD_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return GpfUploadFromFileAlgorithm()

    def name(self):
        return "upload_from_files"

    def displayName(self):
        return self.tr("Création livraison depuis des fichiers")

    def group(self):
        return self.tr("Livraison")

    def groupId(self):
        return "upload"

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
            QgsProcessingParameterFile(
                name=self.FILES,
                description=self.tr(
                    "Fichiers à importer (séparés par ; pour fichiers multiples)"
                ),
                optional=True,
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
        :raises QgsProcessingException: Error in upload creation
        :raises QgsProcessingException: Error in tags add
        :raises QgsProcessingException: Error in file upload
        :raises QgsProcessingException: Error in upload closing
        :return: algorithm results
        :rtype: Dict[str, Any]
        """
        name = self.parameterAsString(parameters, self.NAME, context)
        description = self.parameterAsString(parameters, self.DESCRIPTION, context)
        datastore = self.parameterAsString(parameters, self.DATASTORE, context)
        file_str = self.parameterAsString(parameters, self.FILES, context)
        files = file_str.split(";")

        srs_object = self.parameterAsCrs(parameters, self.SRS, context)
        srs = srs_object.authid()

        tag_data = self.parameterAsMatrix(parameters, self.TAGS, context)
        tags = tags_from_qgs_parameter_matrix_string(tag_data)

        wait_for_close = self.parameterAsBool(parameters, self.WAIT_FOR_CLOSE, context)

        try:
            manager = UploadRequestManager()

            # Create upload
            feedback.pushInfo(self.tr("Création de la livraison"))
            upload = manager.create_upload(
                datastore_id=datastore, name=name, description=description, srs=srs
            )

            # Add tags
            if len(tags) != 0:
                feedback.pushInfo(self.tr("Ajout des tags {}").format(tags))
                manager.add_tags(
                    datastore_id=datastore, upload_id=upload._id, tags=tags
                )

            progress_tag = {
                "integration_progress": '{"send_files_api":"in_progress","wait_checks":"waiting","integration_processing":"waiting"}',
                "integration_current_step": "0",
            }
            feedback.pushInfo(self.tr("Ajout des tags {}").format(progress_tag))
            manager.add_tags(datastore_id=datastore, upload_id=upload._id, tags=tags)

            # Add files
            for filename in files:
                feedback.pushInfo(self.tr("Ajout fichier {}").format(filename))
                manager.add_file(
                    datastore_id=datastore,
                    upload_id=upload._id,
                    filename=Path(filename),
                )

            # Attente prise en compte des fichiers
            feedback.pushInfo(self.tr("Attente prise en compte des fichiers"))
            tree = manager.get_upload_file_tree(
                datastore_id=datastore, upload_id=upload._id
            )
            while len(tree) != len(files):
                tree = manager.get_upload_file_tree(
                    datastore_id=datastore, upload_id=upload._id
                )
                sleep(PlgOptionsManager.get_plg_settings().status_check_sleep)

            # Attente complètement arbitraire pour être sur de pouvoir faire la fermeture
            feedback.pushInfo(
                self.tr("Attente arbitraire de 10s pour pouvoir faire la fermeture")
            )
            sleep(10)

            # Close upload
            feedback.pushInfo(self.tr("Fermeture de la livraison"))
            manager.close_upload(datastore_id=datastore, upload_id=upload._id)

            progress_tag = {
                "integration_progress": '{"send_files_api":"successful","wait_checks":"in_progress","integration_processing":"waiting"}',
                "integration_current_step": "1",
            }
            feedback.pushInfo(self.tr("Ajout des tags {}").format(progress_tag))
            manager.add_tags(datastore_id=datastore, upload_id=upload._id, tags=tags)

            # Get create upload id
            upload_id = upload._id

            # Update feedback if upload attribute present
            if hasattr(feedback, "created_upload_id"):
                feedback.created_upload_id = upload_id

            if wait_for_close:
                # Wait for upload close after check
                feedback.pushInfo(self.tr("Attente vérification contenu livraison"))
                self._wait_upload_close(datastore, upload_id, feedback)

        except UploadCreationException as exc:
            raise QgsProcessingException(f"Upload creation failed : {exc}")
        except AddTagException as exc:
            raise QgsProcessingException(f"Tag add failed : {exc}")
        except FileUploadException as exc:
            raise QgsProcessingException(f"File upload failed : {exc}")
        except UploadClosingException as exc:
            raise QgsProcessingException(f"Upload closing failed : {exc}")

        return {self.CREATED_UPLOAD_ID: upload_id}

    def _wait_upload_close(
        self,
        datastore: str,
        upload_id: str,
        feedback: QgsProcessingFeedback,
    ) -> None:
        """
        Wait until upload is CLOSED or throw exception if status is UNSTABLE

        Args:
            datastore : (str) datastore id
            upload_id:  (str) upload id
            feedback: (QgsProcessingFeedback) : feedback to cancel wait
        """
        try:
            manager = UploadRequestManager()
            upload = manager.get_upload(datastore_id=datastore, upload_id=upload_id)
            status = UploadStatus(upload.status)
            while status != UploadStatus.CLOSED and status != UploadStatus.UNSTABLE:
                upload = manager.get_upload(datastore_id=datastore, upload_id=upload_id)
                status = UploadStatus(upload.status)
                sleep(PlgOptionsManager.get_plg_settings().status_check_sleep)

                if feedback.isCanceled():
                    return

            if status == UploadStatus.UNSTABLE:
                raise QgsProcessingException(
                    self.tr(
                        "Upload check failed. Check report in dashboard for more details."
                    )
                )

        except UnavailableUploadException as exc:
            raise QgsProcessingException(
                self.tr("Upload read failed : {0}").format(exc)
            )
        except UnavailableUploadException as exc:
            raise QgsProcessingException(
                self.tr("Upload read failed : {0}").format(exc)
            )
