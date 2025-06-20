# standard
import json

# PyQGIS
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
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
from geoplateforme.processing.utils import (
    get_short_string,
    get_user_manual_url,
    tags_from_qgs_parameter_matrix_string,
)
from geoplateforme.toolbelt.preferences import PlgOptionsManager

data_type = "WFS"


class WfsPublicationAlgorithm(QgsProcessingAlgorithm):
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

    RELATIONS_NATIVE_NAME = "native_name"
    RELATIONS_PUBLIC_NAME = "public_name"
    RELATIONS_TITLE = "title"
    RELATIONS_ABSTRACT = "abstract"
    RELATIONS_KEYWORDS = "keywords"

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
        return WfsPublicationAlgorithm()

    def name(self):
        return "wfs_publish"

    def displayName(self):
        return self.tr("Publication service WFS")

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
        datastore = self.parameterAsString(parameters, self.DATASTORE, context)
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

        tag_data = self.parameterAsMatrix(parameters, self.TAGS, context)
        tags = tags_from_qgs_parameter_matrix_string(tag_data)

        sandbox_datastore_ids = (
            PlgOptionsManager.get_plg_settings().sandbox_datastore_ids
        )
        if datastore in sandbox_datastore_ids and not layer_name.startswith("SANDBOX"):
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
                datastore_id=datastore,
                _type=ConfigurationType.WFS,
                _metadata=metadata,
                _name=name,
                _layer_name=layer_name,
                _type_infos={
                    "used_data": [
                        {
                            "stored_data": stored_data_id,
                            "relations": relations,
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
                datastore=datastore,
                configuration=configuration,
            )
            configuration_id = res

        except ConfigurationCreationException as exc:
            raise QgsProcessingException(f"exc configuration id : {exc}")

        # get the endpoint for the publication
        try:
            manager_endpoint = DatastoreRequestManager()
            res = manager_endpoint.get_endpoint(
                datastore=datastore, data_type=data_type
            )

            publication_endpoint = res
        except UnavailableEndpointException as exc:
            raise QgsProcessingException(f"exc endpoint : {exc}")

        # create publication (offering)
        try:
            manager_offering = OfferingsRequestManager()
            offering = manager_offering.create_offering(
                visibility=publication_visibility,
                endpoint=publication_endpoint,
                datastore=datastore,
                configuration_id=configuration_id,
            )
        except OfferingCreationException as exc:
            raise QgsProcessingException(f"exc publication url : {exc}")

        try:
            # Update configuration tags
            manager_configuration = ConfigurationRequestManager()
            manager_configuration.add_tags(
                datastore_id=datastore,
                configuration_id=configuration_id,
                tags=tags,
            )
        except AddTagException as exc:
            raise QgsProcessingException(f"exc tag update url : {exc}")

        try:
            # Update stored data tags
            manager = StoredDataRequestManager()
            manager.add_tags(
                datastore_id=datastore,
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
            self.RELATIONS_NATIVE_NAME,
            self.RELATIONS_TITLE,
            self.RELATIONS_ABSTRACT,
        ]
        for compo in data:
            missing_keys = [key for key in mandatory_keys if key not in compo]

            if missing_keys:
                raise QgsProcessingException(
                    f"Missing {', '.join(missing_keys)} keys for {self.RELATIONS} item in input json."
                )
