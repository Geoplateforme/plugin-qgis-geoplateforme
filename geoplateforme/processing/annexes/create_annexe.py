# standard

# PyQGIS

from pathlib import Path

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.annexes import AnnexeRequestManager
from geoplateforme.api.custom_exceptions import AnnexeFileUploadException
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class CreateAnnexeAlgorithm(QgsProcessingAlgorithm):
    DATASTORE_ID = "DATASTORE_ID"
    FILE_PATH = "FILE_PATH"
    PUBLIC_PATHS = "PUBLIC_PATHS"
    PUBLISHED = "PUBLISHED"
    LABELS = "LABELS"

    CREATED_ANNEXE_ID = "CREATED_ANNEXE_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return CreateAnnexeAlgorithm()

    def name(self):
        return "create_annexe"

    def displayName(self):
        return self.tr("Création d'une annexe dans l'entrepôt")

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
            QgsProcessingParameterFile(
                self.FILE_PATH,
                self.tr("Fichier annexe"),
                fileFilter="Fichier annexe (*.*)",
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.PUBLIC_PATHS,
                description=self.tr(
                    "Chemins dans l'URL publique. Valeurs séparées par des ,"
                ),
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.PUBLISHED,
                description=self.tr("Publication de l'annexe ?"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.LABELS,
                description=self.tr("Liste des étiquettes. Valeurs séparées par des ,"),
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.CREATED_ANNEXE_ID,
                description=self.tr("Identifiant de l'annexe créée."),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore = self.parameterAsString(parameters, self.DATASTORE_ID, context)
        public_path_str = self.parameterAsString(parameters, self.PUBLIC_PATHS, context)
        public_paths = []
        if public_path_str:
            public_paths = public_path_str.split(",")

        labels_str = self.parameterAsString(parameters, self.LABELS, context)
        labels = []
        if labels_str:
            labels = labels_str.split(",")

        published = self.parameterAsBool(parameters, self.PUBLISHED, context)
        file_path = self.parameterAsFile(parameters, self.FILE_PATH, context)

        try:
            manager = AnnexeRequestManager()
            annexe = manager.create_annexe(
                datastore_id=datastore,
                file_path=Path(file_path),
                public_paths=public_paths,
                published=published,
                labels=labels,
            )

        except AnnexeFileUploadException as exc:
            raise QgsProcessingException(
                f"Erreur lors de la création d'une annexe : {exc}"
            )

        return {
            self.CREATED_ANNEXE_ID: annexe._id,
        }
