# standard
import json

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

from geoplateforme.api.configuration import (
    Configuration,
    ConfigurationRequestManager,
    ConfigurationType,
)

# Plugin
from geoplateforme.api.custom_exceptions import (
    AddTagException,
    ConfigurationCreationException,
    OfferingCreationException,
    UnavailableEndpointException,
)
from geoplateforme.api.datastore import DatastoreRequestManager
from geoplateforme.api.offerings import OfferingsRequestManager
from geoplateforme.api.stored_data import StoredDataRequestManager
from geoplateforme.processing.tools.create_geoserver_style import (
    CreateGeoserverStyleAlgorithm,
)
from geoplateforme.processing.utils import (
    get_short_string,
    get_user_manual_url,
    tags_from_qgs_parameter_matrix_string,
)
from geoplateforme.toolbelt.preferences import PlgOptionsManager

data_type = "WMS-VECTOR"


class WmsPublicationAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    STORED_DATA = "STORED_DATA"
    NAME = "NAME"
    LAYER_NAME = "LAYER_NAME"  # Equivalent nom technique

    RELATIONS = "RELATIONS"

    TITLE = "TITLE"
    ABSTRACT = "ABSTRACT"
    KEYWORDS = "KEYWORDS"

    TAGS = "TAGS"

    URL_ATTRIBUTION = "URL_ATTRIBUTION"
    URL_TITLE = "URL_TITLE"

    RELATIONS_NAME = "name"
    RELATIONS_STYLE_FILE = "style"
    RELATIONS_FTL_FILE = "ftl"

    # Parameter not yet implemented
    METADATA = "metadata"
    VISIBILITY = "visibility"

    OFFERING_ID = "OFFERING_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return WmsPublicationAlgorithm()

    def name(self):
        return "wms_publish"

    def displayName(self):
        return self.tr("Publication service WMS-VECTOR")

    def group(self):
        return self.tr("Publication")

    def groupId(self):
        return "publication"

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
                name=self.STORED_DATA,
                description=self.tr("Identifiant de la base de données vectorielle"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.NAME,
                description=self.tr("Nom de la publication"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.LAYER_NAME,
                description=self.tr("Nom technique de la publication"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.RELATIONS,
                description=self.tr("JSON pour les relations"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.TITLE,
                description=self.tr("Titre de la publication"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.ABSTRACT,
                description=self.tr("Résumé de la publication"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.KEYWORDS,
                description=self.tr("Mot clé de la publication"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.URL_ATTRIBUTION,
                description=self.tr("Url attribution"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.URL_TITLE,
                description=self.tr("Titre attribution"),
            )
        )

        self.addParameter(
            QgsProcessingParameterMatrix(
                name=self.TAGS,
                description=self.tr("Tags"),
                headers=[self.tr("Tag"), self.tr("Valeur")],
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.OFFERING_ID,
                description=self.tr("Identifiant de l'offre créée."),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE, context)
        stored_data_id = self.parameterAsString(parameters, self.STORED_DATA, context)
        name = self.parameterAsString(parameters, self.NAME, context)
        layer_name = self.parameterAsString(parameters, self.LAYER_NAME, context)
        title = self.parameterAsString(parameters, self.TITLE, context)

        url = self.parameterAsString(parameters, self.URL_ATTRIBUTION, context)
        url_title = self.parameterAsString(parameters, self.URL_TITLE, context)
        abstract = self.parameterAsString(parameters, self.ABSTRACT, context)

        relations_str = self.parameterAsString(parameters, self.RELATIONS, context)
        relations: list[dict[str, str]] | None = None
        if relations_str:
            relations = json.loads(relations_str)
            self._check_relation(relations)

        relations_with_id: list[dict[str, str]] = []

        for relation in relations:
            # Create new static file
            id_style = self._create_geoserver_style(
                datastore=datastore_id,
                name=relation[self.RELATIONS_NAME],
                file_path=relation[self.RELATIONS_STYLE_FILE],
                feedback=feedback,
                context=context,
            )
            relation_with_id = {
                "name": relation[self.RELATIONS_NAME],
                "style": id_style,
            }
            # TODO : manage ftl file

            relations_with_id.append(relation_with_id)

        tag_data = self.parameterAsMatrix(parameters, self.TAGS, context)
        tags = tags_from_qgs_parameter_matrix_string(tag_data)

        sandbox_datastore_ids = (
            PlgOptionsManager.get_plg_settings().sandbox_datastore_ids
        )
        if datastore_id in sandbox_datastore_ids and not layer_name.startswith(
            "SANDBOX"
        ):
            layer_name = f"SANDBOX_{layer_name}"
            feedback.pushInfo(
                self.tr(
                    "L'entrepot utilisé est un bac à sable et le prefix SANDBOX est obligatoire pour le nom de la couche. Nouveau nom du couche : {}"
                ).format(layer_name)
            )

        # TODO : add metadata and visibility
        metadata = []
        publication_visibility = "PUBLIC"

        # create (post) configuration from input data
        try:
            manager_configuration = ConfigurationRequestManager()

            configuration = Configuration(
                _id="",
                datastore_id=datastore_id,
                _type=ConfigurationType.WMS_VECTOR,
                _metadata=metadata,
                _name=name,
                _layer_name=layer_name,
                _type_infos={
                    "used_data": [
                        {
                            "stored_data": stored_data_id,
                            "relations": relations_with_id,
                        }
                    ]
                },
                _attribution={},
                is_detailed=True,
            )
            configuration.title = title
            configuration.abstract = abstract
            configuration.url_title = url_title
            configuration.url = url

            # response = configuration
            res = manager_configuration.create_configuration(
                datastore=datastore_id,
                configuration=configuration,
            )
            configuration_id = res

        except ConfigurationCreationException as exc:
            raise QgsProcessingException(f"exc configuration id : {exc}")

        # get the endpoint for the publication
        try:
            datastore_manager = DatastoreRequestManager()
            datastore = datastore_manager.get_datastore(datastore_id)
            res = datastore.get_endpoint(data_type=data_type)

            publication_endpoint = res
        except UnavailableEndpointException as exc:
            raise QgsProcessingException(f"exc endpoint : {exc}")

        # create publication (offering)
        try:
            manager_offering = OfferingsRequestManager()
            offering = manager_offering.create_offering(
                visibility=publication_visibility,
                endpoint=publication_endpoint,
                datastore=datastore_id,
                configuration_id=configuration_id,
            )
        except OfferingCreationException as exc:
            raise QgsProcessingException(f"exc publication url : {exc}")

        try:
            # Update configuration tags
            manager_configuration = ConfigurationRequestManager()
            manager_configuration.add_tags(
                datastore_id=datastore_id,
                configuration_id=configuration_id,
                tags=tags,
            )
        except AddTagException as exc:
            raise QgsProcessingException(f"exc tag update url : {exc}")

        try:
            # Update stored data tags
            manager = StoredDataRequestManager()
            manager.add_tags(
                datastore_id=datastore_id,
                stored_data_id=stored_data_id,
                tags={"published": "true"},
            )
        except AddTagException as exc:
            raise QgsProcessingException(f"exc tag update url : {exc}")

        return {
            self.OFFERING_ID: offering._id,
        }

    def _check_relation(self, data) -> None:
        """
        Check relation data, raises QgsProcessingException in case of errors

        Args:
            data: input composition data
        """
        if not isinstance(data, list):
            raise QgsProcessingException(
                f"Invalid {self.RELATIONS} key in input json.  Expected list, not {type(data)}"
            )

        mandatory_keys = [
            self.RELATIONS_NAME,
            self.RELATIONS_STYLE_FILE,
        ]
        for compo in data:
            missing_keys = [key for key in mandatory_keys if key not in compo]

            if missing_keys:
                raise QgsProcessingException(
                    f"Missing {', '.join(missing_keys)} keys for {self.RELATIONS} item in input json."
                )

    def _create_geoserver_style(
        self,
        datastore_id: str,
        name: str,
        file_path: str,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> str:
        """Create a geoserver style static in datastore

        :param name: static name
        :type name: str
        :param datastore_id: datastore id
        :type datastore_id: str
        :param file_path: path to file
        :type file_path: str
        :param context: context of processing
        :type context: QgsProcessingContext
        :param feedback: feedback for processing
        :type feedback: QgsProcessingFeedback
        :raises QgsProcessingException: an error occured when creating the database
        :return: create static id
        :rtype: str
        """

        algo_str = f"geoplateforme:{CreateGeoserverStyleAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)
        params = {
            CreateGeoserverStyleAlgorithm.DATASTORE: datastore_id,
            CreateGeoserverStyleAlgorithm.NAME: name,
            CreateGeoserverStyleAlgorithm.FILE_PATH: file_path,
        }
        results, successful = alg.run(params, context, feedback)
        if successful:
            static_id = results[CreateGeoserverStyleAlgorithm.ID_STATIC]
        else:
            raise QgsProcessingException(
                self.tr(
                    "Ajout du fichier de style .sld {} dans l'entrepot à échoué."
                ).format(file_path)
            )
        return static_id
