# standard

# PyQGIS

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.custom_exceptions import UnavailableOfferingsException
from geoplateforme.api.offerings import OfferingsRequestManager
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class DeleteOfferingAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    OFFERING = "OFFERING"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return DeleteOfferingAlgorithm()

    def name(self):
        return "delete_offering"

    def displayName(self):
        return self.tr("Suppression d'une offre")

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
                name=self.OFFERING,
                description=self.tr("Identifiant de l'offre"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE, context)
        offering_id = self.parameterAsString(parameters, self.OFFERING, context)
        try:
            feedback.pushInfo(self.tr("Suppression de l'offre"))
            manager_stored = OfferingsRequestManager()
            manager_stored.delete_offering(datastore_id, offering_id)

        except UnavailableOfferingsException as exc:
            print(self.tr("Erreur lors de la suppression de l'offre : {}").format(exc))
            raise QgsProcessingException(
                self.tr("Erreur lors de la suppression de l'offre : {}").format(exc)
            ) from exc

        return {}
