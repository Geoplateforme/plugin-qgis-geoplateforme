# standard

# PyQGIS

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.custom_exceptions import CreateUserKeyException
from geoplateforme.api.user_key import UserKeyRequestManager, UserKeyType
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class CreateOAuthKeyAlgorithm(QgsProcessingAlgorithm):
    NAME = "NAME"
    WHITELIST = "WHITELIST"
    BLACKLIST = "BLACKLIST"
    USER_AGENT = "USER_AGENT"
    REFERER = "REFERER"

    CREATED_KEY_ID = "CREATED_KEY_ID"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return CreateOAuthKeyAlgorithm()

    def name(self):
        return "create_oauth_key"

    def displayName(self):
        return self.tr("Création d'une clé OAuth2 pour l'utilisateur")

    def group(self):
        return self.tr("Clés")

    def groupId(self):
        return "user_key"

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                name=self.NAME,
                description=self.tr("Nom de la clé"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.WHITELIST,
                description=self.tr("Adresses IP authorisées. Valeurs séparées par ,"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.BLACKLIST,
                description=self.tr(
                    "Adresses IP non authorisées. Valeurs séparées par ,"
                ),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.USER_AGENT,
                description=self.tr("User-agent"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.REFERER,
                description=self.tr("Referer"),
                optional=True,
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                name=self.CREATED_KEY_ID,
                description=self.tr("Identifiant de la clé créée"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        name = self.parameterAsString(parameters, self.NAME, context)
        whitelist_str = self.parameterAsString(parameters, self.WHITELIST, context)
        if whitelist_str:
            whitelist = whitelist_str.split(",")
        else:
            whitelist = None

        blacklist_str = self.parameterAsString(parameters, self.BLACKLIST, context)
        if blacklist_str:
            blacklist = blacklist_str.split(",")
        else:
            blacklist = None

        user_agent = self.parameterAsString(parameters, self.USER_AGENT, context)
        referer = self.parameterAsString(parameters, self.REFERER, context)

        try:
            feedback.pushInfo(self.tr("Création de la clé"))
            manager = UserKeyRequestManager()
            user_key = manager.create_user_key(
                name=name,
                user_key_type=UserKeyType.OAUTH2,
                type_infos={},
                whitelist=whitelist,
                blacklist=blacklist,
                user_agent=user_agent if user_agent else None,
                referer=referer if referer else None,
            )
            return {
                self.CREATED_KEY_ID: user_key._id,
            }

        except CreateUserKeyException as exc:
            raise QgsProcessingException(
                self.tr("Erreur lors de la création de la clé : {}").format(exc)
            ) from exc

        return {}
