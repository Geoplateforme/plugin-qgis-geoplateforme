# standard

# PyQGIS

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.custom_exceptions import CreatePermissionException
from geoplateforme.api.permissions import PermissionRequestManager, PermissionType
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class CreatePermissionAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    LICENCE = "LICENCE"
    PERMISSION_TYPE = "PERMISSION_TYPE"
    USER_OR_COMMUNITIES = "USER_OR_COMMUNITIES"
    OFFERINGS = "OFFERINGS"
    END_DATE = "END_DATE"
    ONLY_OAUTH = "ONLY_OAUTH"

    PERMISSION_TYPE_ENUM = ["ACCOUNT", "COMMUNITY"]

    CREATED_PERMISSIONS_ID = "CREATED_PERMISSIONS_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return CreatePermissionAlgorithm()

    def name(self):
        return "create_permission"

    def displayName(self):
        return self.tr("Création d'une permission pour l'entrepôt")

    def group(self):
        return self.tr("Permissions")

    def groupId(self):
        return "permissions"

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
                name=self.LICENCE,
                description=self.tr("Nom de la permission"),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.PERMISSION_TYPE,
                description=self.tr("Type de permission."),
                options=self.PERMISSION_TYPE_ENUM,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.OFFERINGS,
                description=self.tr(
                    "Identifiants des offres. Valeurs séparées par des virgules (,)"
                ),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.USER_OR_COMMUNITIES,
                description=self.tr(
                    "Identifiants des utilisateurs ou communautés. Valeurs séparées par des virgules (,)"
                ),
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                name=self.END_DATE,
                description=self.tr("Date de fin de la permission"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.ONLY_OAUTH,
                description=self.tr(
                    "Authentification forte (compatible uniquement avec clé OAUTH)"
                ),
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE, context)
        license_ = self.parameterAsString(parameters, self.LICENCE, context)
        permission_type_str = self.parameterAsEnumString(
            parameters, self.PERMISSION_TYPE, context
        )
        if permission_type_str not in self.PERMISSION_TYPE_ENUM:
            raise QgsProcessingException(
                self.tr(
                    "Type de permission invalide. Valeurs supportées : {}".format(
                        ",".join(self.PERMISSION_TYPE_ENUM)
                    )
                )
            )

        user_or_communities_str = self.parameterAsString(
            parameters, self.USER_OR_COMMUNITIES, context
        )
        user_or_communities = user_or_communities_str.split(",")

        offerring_str = self.parameterAsString(parameters, self.OFFERINGS, context)
        offerings = offerring_str.split(",")

        end_date = self.parameterAsDateTime(parameters, self.END_DATE, context)
        if not end_date.isNull():
            end_date = end_date.toUTC().toPyDateTime()
        else:
            end_date = None

        only_oauth = None
        if self.ONLY_OAUTH in parameters:
            only_oauth = self.parameterAsBool(parameters, self.ONLY_OAUTH, context)

        try:
            feedback.pushInfo(self.tr("Création de la permission"))
            manager = PermissionRequestManager()
            permissions = manager.create_permission(
                datastore_id=datastore_id,
                licence=license_,
                permission_type=PermissionType(permission_type_str),
                users_or_communities=user_or_communities,
                offerings=offerings,
                end_date=end_date,
                only_oauth=only_oauth,
            )

            return {
                self.CREATED_PERMISSIONS_ID: [
                    permission._id for permission in permissions
                ]
            }

        except CreatePermissionException as exc:
            raise QgsProcessingException(
                self.tr("Erreur lors de la création de la permission : {}").format(exc)
            ) from exc

        return {}
