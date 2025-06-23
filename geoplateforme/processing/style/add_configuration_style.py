# standard
import uuid
from pathlib import Path

from qgis.core import (
    QgsApplication,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.configuration import ConfigurationRequestManager
from geoplateforme.api.custom_exceptions import (
    ReadConfigurationException,
    UnavailableDatastoreException,
    UpdateConfigurationException,
)
from geoplateforme.api.datastore import DatastoreRequestManager
from geoplateforme.processing.annexes.create_annexe import CreateAnnexeAlgorithm
from geoplateforme.processing.utils import get_short_string, get_user_manual_url
from geoplateforme.toolbelt.preferences import PlgOptionsManager

# PyQGIS


class AddConfigurationStyleAlgorithm(QgsProcessingAlgorithm):
    DATASTORE_ID = "DATASTORE_ID"
    CONFIGURATION_ID = "CONFIGURATION_ID"
    STYLE_NAME = "STYLE_NAME"
    DATASET_NAME = "DATASET_NAME"
    STYLE_FILE_PATHS = "STYLE_FILE_PATHS"
    LAYER_STYLE_NAMES = "LAYER_STYLE_NAMES"

    CREATED_ANNEXE_IDS = "CREATED_ANNEXE_IDS"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return AddConfigurationStyleAlgorithm()

    def name(self):
        return "add_configuration_style"

    def displayName(self):
        return self.tr("Ajout d'un style pour une configuration")

    def group(self):
        return self.tr("Styles")

    def groupId(self):
        return "styles"

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
                name=self.CONFIGURATION_ID,
                description=self.tr("Identifiant de la configuration"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.STYLE_NAME,
                self.tr("Nom du style"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DATASET_NAME,
                self.tr("Nom du jeu de données"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.STYLE_FILE_PATHS,
                self.tr("Fichier(s) de style. Valeurs séparées par des ,"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER_STYLE_NAMES,
                self.tr("Nom(s) de couche pour style. Valeurs séparées par des ,"),
                optional=True,
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.CREATED_ANNEXE_IDS,
                description=self.tr(
                    "Identifiants des annexes créées. Valeurs séparées par des ,"
                ),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE_ID, context)
        config_id = self.parameterAsString(parameters, self.CONFIGURATION_ID, context)
        dataset_name = self.parameterAsString(parameters, self.DATASET_NAME, context)
        style_name = self.parameterAsString(parameters, self.STYLE_NAME, context)

        style_file_str = self.parameterAsString(
            parameters, self.STYLE_FILE_PATHS, context
        )
        style_files = style_file_str.split(",")

        layer_style_name_str = self.parameterAsString(
            parameters, self.LAYER_STYLE_NAMES, context
        )
        layer_style_names = []
        if layer_style_name_str:
            layer_style_names = layer_style_name_str.split(",")

            if len(style_files) != len(layer_style_names):
                raise QgsProcessingException(
                    self.tr(
                        "Il est nécessaire d'avoir autant de nom de couche que de fichier de style. Fournis {}, attendu {} ".format(
                            len(layer_style_names), len(style_files)
                        )
                    )
                )

        created_annexe_ids = []
        created_annexe_public_path = []
        # Create annexe file
        feedback.pushInfo(self.tr("Création des fichiers d'annexe"))
        for style_file in style_files:
            file_path = Path(style_file)
            labels = ["type=style"]
            if dataset_name:
                labels.append(f"datasheet_name={dataset_name}")

            style_uuid = uuid.uuid4()
            style_path = f"/style/{style_uuid}{file_path.suffix}"
            created_annexe_public_path.append(style_path)

            created_annexe_id = self._create_annexe(
                datastore_id=datastore_id,
                file_path=file_path,
                public_path=style_path,
                labels=labels,
                context=context,
                feedback=feedback,
            )
            created_annexe_ids.append(created_annexe_id)

        # Get configuration
        feedback.pushInfo(self.tr("Récupération de la configuration"))
        config_manager = ConfigurationRequestManager()
        try:
            config = config_manager.get_configuration(
                datastore=datastore_id, configuration=config_id
            )
        except ReadConfigurationException as exc:
            raise QgsProcessingException(
                f"Erreur lors de la lecture de la configuration : {exc}"
            ) from exc

        # Get datastore (needed to get url for annexe)
        feedback.pushInfo(self.tr("Récupération de l'entrepôt"))
        try:
            datastore_manager = DatastoreRequestManager()
            datastore = datastore_manager.get_datastore(datastore=datastore_id)

        except UnavailableDatastoreException as exc:
            raise QgsProcessingException(
                f"Erreur lors de la lecture de l'entrepôt : {exc}"
            ) from exc

        # Define new extra for configuration
        feedback.pushInfo(self.tr("Modification de la configuration"))
        settings = PlgOptionsManager.get_plg_settings()
        url_api_entrepot = settings.url_api_entrepot
        url_entrepot = url_api_entrepot.removesuffix("/api")

        config_extra = config.extra
        config_styles = []
        if "styles" in config_extra:
            config_styles = config_extra["styles"]

        layer_list = []
        for i, created_annexe_id in enumerate(created_annexe_ids):
            url_annexe = f"{url_entrepot}/annexes/{datastore.technical_name}{created_annexe_public_path[i]}"
            layer_dict = {"url": url_annexe, "annexe_id": created_annexe_id}
            if layer_style_name_str:
                layer_dict["name"] = layer_style_names[i]
            layer_list.append(layer_dict)

        config_styles.append(
            {
                "name": style_name,
                "layers": layer_list,
            }
        )
        # Update configuration
        config_extra["styles"] = config_styles

        try:
            config_manager.update_extra_and_name(
                datastore_id=datastore_id,
                configuration_id=config_id,
                extra=config_extra,
            )
        except UpdateConfigurationException as exc:
            raise QgsProcessingException(
                f"Erreur lors de la lecture de la configuration : {exc}"
            ) from exc

        return {self.CREATED_ANNEXE_IDS: ",".join(created_annexe_ids)}

    def _create_annexe(
        self,
        datastore_id: str,
        file_path: Path,
        public_path: str,
        labels: list[str],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> str:
        """Create annexe to be referenced in configuration extra dict

        :param datastore_id: datastore id
        :type datastore_id: str
        :param file_path: file path for annexe
        :type file_path: Path
        :param public_path: public path for annexe
        :type public_path: str
        :param labels: labelse
        :type labels: list[str]
        :param context: context
        :type context: QgsProcessingContext
        :param feedback: feedbakc
        :type feedback: QgsProcessingFeedback
        :raises QgsProcessingException: error when annexe creation fail
        :return: created annexe id
        :rtype: str
        """
        algo_str = f"geoplateforme:{CreateAnnexeAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)
        params = {
            CreateAnnexeAlgorithm.DATASTORE_ID: datastore_id,
            CreateAnnexeAlgorithm.FILE_PATH: str(file_path),
            CreateAnnexeAlgorithm.PUBLIC_PATHS: public_path,
            CreateAnnexeAlgorithm.PUBLISHED: True,
            CreateAnnexeAlgorithm.LABELS: ",".join(labels),
        }
        results, successful = alg.run(params, context, feedback)
        if successful:
            created_annexe_id = results[CreateAnnexeAlgorithm.CREATED_ANNEXE_ID]
        else:
            raise QgsProcessingException(
                self.tr("Erreur lors de la création de l'annexe")
            )
        return created_annexe_id
