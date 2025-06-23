# standard

# PyQGIS

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.annexes import AnnexeRequestManager
from geoplateforme.api.custom_exceptions import DeleteAnnexeException
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class DeleteAnnexeAlgorithm(QgsProcessingAlgorithm):
    DATASTORE_ID = "DATASTORE_ID"
    ANNEXE_ID = "ANNEXE_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return DeleteAnnexeAlgorithm()

    def name(self):
        return "delete_annexe"

    def displayName(self):
        return self.tr("Suppression d'une annexe")

    def group(self):
        return self.tr("Annexes")

    def groupId(self):
        return "annexes"

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                name=self.DATASTORE_ID,
                description=self.tr("Identifiant de l'entrepôt"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.ANNEXE_ID,
                description=self.tr("Identifiant de l'annexe'"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE_ID, context)
        annex_id = self.parameterAsString(parameters, self.ANNEXE_ID, context)
        try:
            feedback.pushInfo(self.tr("Suppression de l'annexe"))
            manager = AnnexeRequestManager()
            manager.delete(datastore_id=datastore_id, annexe_id=annex_id)

        except DeleteAnnexeException as exc:
            raise QgsProcessingException(
                self.tr("Erreur lors de la suppression de l'annexe : {}").format(exc)
            ) from exc

        return {}
