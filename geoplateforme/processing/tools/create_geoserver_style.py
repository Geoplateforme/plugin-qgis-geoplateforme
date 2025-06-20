# standard

# PyQGIS
from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.custom_exceptions import StaticFileUploadException
from geoplateforme.api.static import StaticRequestManager, StaticType
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class CreateGeoserverStyleAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    FILE_PATH = "FILE_PATH"
    NAME = "NAME"
    DESCRIPTION = "DESCRIPTION"

    ID_STATIC = "ID_STATIC"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return CreateGeoserverStyleAlgorithm()

    def name(self):
        return "create_geoserver_style"

    def displayName(self):
        return self.tr("Ajout style Geoserver dans l'entrepôt")

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
            QgsProcessingParameterFile(
                self.FILE_PATH,
                self.tr("Fichier style Geoserver"),
                fileFilter="Fichier style Geoserver (*.sld)",
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.NAME,
                description=self.tr("Nom du fichier"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.DESCRIPTION,
                description=self.tr("Description du fichier"),
                optional=True,
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.ID_STATIC,
                description=self.tr("Identifiant de la donnée statique crée"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore = self.parameterAsString(parameters, self.DATASTORE, context)
        name = self.parameterAsString(parameters, self.NAME, context)
        description = self.parameterAsString(parameters, self.DESCRIPTION, context)
        file_path = self.parameterAsFile(parameters, self.FILE_PATH, context)

        try:
            manager_static = StaticRequestManager()
            static_id = manager_static.create_static(
                datastore_id=datastore,
                file_path=Path(file_path),
                name=name,
                static_type=StaticType.GEOSERVER_STYLE,
                description=description,
            )

        except StaticFileUploadException as exc:
            raise QgsProcessingException(f"exc static creation : {exc}")

        return {
            self.ID_STATIC: static_id,
        }
