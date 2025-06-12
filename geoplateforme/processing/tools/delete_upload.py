# standard

# PyQGIS

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.custom_exceptions import DeleteUploadException
from geoplateforme.api.upload import UploadRequestManager
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class DeleteUploadAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    UPLOAD = "UPLOAD"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return DeleteUploadAlgorithm()

    def name(self):
        return "delete_upload"

    def displayName(self):
        return self.tr("Suppression d'une livraison")

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

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE, context)
        upload_id = self.parameterAsString(parameters, self.UPLOAD, context)
        try:
            feedback.pushInfo(self.tr("Suppression de la livraison"))
            manager_stored = UploadRequestManager()
            manager_stored.delete(datastore_id, upload_id)

        except DeleteUploadException as exc:
            raise QgsProcessingException(
                self.tr("Erreur lors de la suppression de la livraison : {}").format(
                    exc
                )
            ) from exc

        return {}
