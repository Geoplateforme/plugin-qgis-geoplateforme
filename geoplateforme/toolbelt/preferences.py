#! python3  # noqa: E265

"""
Plugin settings.
"""

# standard
from dataclasses import asdict, dataclass, fields
from typing import List, Optional

# PyQGIS
from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsSettings

# package
import geoplateforme.toolbelt.log_handler as log_hdlr
from geoplateforme.__about__ import __title__, __version__
from geoplateforme.datamodels import oauth2_configuration
from geoplateforme.toolbelt.env_var_parser import EnvVarParser

# ############################################################################
# ########## Classes ###############
# ##################################

CFG_AUTH_NAME = "geoplateforme_cfg"
PREFIX_ENV_VARIABLE = "QGIS_GEOPLATEFORME_"


@dataclass
class PlgEnvVariableSettings:
    """Plugin settings from environnement variable"""

    def env_variable_used(self, attribute: str, default_from_name: bool = True) -> str:
        """Get environnement variable used for environnement variable settings

        :param attribute: attribute to check
        :type attribute: str
        :param default_from_name: define default environnement value from attribute
        name PREFIX_ENV_VARIABLE_<upper case attribute>
        :type default_from_name: bool
        :return: environnement variable used
        :rtype: str
        """
        settings_env_variable = asdict(self)
        env_variable = settings_env_variable.get(attribute, "")
        if not env_variable and default_from_name:
            env_variable = f"{PREFIX_ENV_VARIABLE}{attribute}".upper()
        return env_variable


@dataclass
class PlgSettingsStructure:
    """Plugin settings structure and defaults values."""

    # global
    debug_mode: bool = False
    version: str = __version__

    # network and authentication
    url_geoplateforme: str = "https://cartes.gouv.fr/"
    url_api_entrepot: str = "https://data.geopf.fr/api"
    qgis_auth_id: Optional[str] = None

    # status check sleep (in seconds)
    status_check_sleep: int = 30

    # sandbox datastores
    sandbox_datastore_ids_str: str = (
        "122b878c-aad8-4507-87b2-465e664467d3,87e1beb6-ee07-4adc-8449-6a925dc28949"
    )

    # processing names
    vector_db_generation_processing_names_str: str = "Intégration de données vecteur livrées en base,Intégration de données vecteur livrées en base (Bac à sable)"

    vector_tile_generation_processing_names_str: str = "Calcul de pyramide vecteur,Calcul de pyramide vecteur (Bac à sable),Calcul ou mise à jour de pyramide vecteur"

    # processing ids
    raster_tiles_from_wms_vector_processing_ids_str: str = (
        "6a54dc92-fc93-4c8e-9f02-046bf889550e,2e56e7ba-552b-49b8-abcf-563184dd8c55"
    )

    @property
    def base_url_api_entrepot(self) -> str:
        """Return the URL for API entrepot"""
        return f"{self.url_api_entrepot}"

    @property
    def sandbox_datastore_ids(self) -> List[str]:
        """Return list of datastore id considered as sandbox.

        :return: list of sandbox datastore id
        :rtype: List[str]
        """
        return self.sandbox_datastore_ids_str.split(",")

    @property
    def vector_db_generation_processing_names(self) -> List[str]:
        """Return list name possible for vector db generation processing.

        :return: list of name for processing
        :rtype: List[str]
        """
        return self.vector_db_generation_processing_names_str.split(",")

    @property
    def vector_tile_generation_processing_names(self) -> List[str]:
        """Return list name possible for vector tile generation processing.

        :return: list of name for processing
        :rtype: List[str]
        """
        return self.vector_tile_generation_processing_names_str.split(",")

    @property
    def raster_tiles_from_wms_vector_processing_ids(self) -> List[str]:
        """Return list name possible for vector tile generation processing.

        :return: list of name for processing
        :rtype: List[str]
        """
        return self.raster_tiles_from_wms_vector_processing_ids_str.split(",")

    def create_auth_config(self) -> Optional[QgsAuthMethodConfig]:
        """Create QgsAuthMethodConfig for OAuth2 authentification.

        :return: created configuration. Warning: config must be added to QgsApplication.authManager() before use
        :rtype: Optional[QgsAuthMethodConfig]
        """
        new_auth_config = QgsAuthMethodConfig(method="OAuth2", version=1)
        new_auth_config.setId(QgsApplication.authManager().uniqueConfigId())
        new_auth_config.setName(CFG_AUTH_NAME)

        # load OAuth2 configuration from JSON file
        auth_config_obj = oauth2_configuration.OAuth2Configuration.from_json()
        if not isinstance(auth_config_obj, oauth2_configuration.OAuth2Configuration):
            log_hdlr.PlgLogger.log(
                message="Error while loading authentication configuration.",
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return

        # We need to use a string for config_map
        auth_config_as_str = auth_config_obj.as_qgis_str_config_map()
        config_map = {"oauth2config": auth_config_as_str}
        new_auth_config.setConfigMap(config_map)

        if not new_auth_config.isValid():
            log_hdlr.PlgLogger.log(
                message="Error while creating authentication configuration NOT VALID.",
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return

        log_hdlr.PlgLogger.log(
            message=f"Authentication configuration created with ID: {new_auth_config.id()} "
            f"({new_auth_config.name()})",
            log_level=Qgis.MessageLevel.Success,
        )

        return new_auth_config


class PlgOptionsManager:
    """Plugin settings manager."""

    @staticmethod
    def disconnect() -> None:
        """
        Disconnect current user and remove authentication configuration

        """
        plg_settings = PlgOptionsManager.get_plg_settings()

        # Remove current authentication configuration
        if plg_settings.qgis_auth_id:
            auth_manager = QgsApplication.authManager()
            auth_manager.removeAuthenticationConfig(plg_settings.qgis_auth_id)

        plg_settings.qgis_auth_id = None
        PlgOptionsManager.save_from_object(plg_settings)

    @staticmethod
    def get_plg_settings() -> PlgSettingsStructure:
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings
        :rtype: PlgSettingsStructure
        """
        # get dataclass fields definition
        settings_fields = fields(PlgSettingsStructure)
        env_variable_settings = PlgEnvVariableSettings()

        # retrieve settings from QGIS/Qt
        settings = QgsSettings()
        settings.beginGroup(__title__)

        # map settings values to preferences object
        li_settings_values = []
        for i in settings_fields:
            try:
                value = settings.value(key=i.name, defaultValue=i.default, type=i.type)
                # If environnement variable used, get value from environnement variable
                env_variable = env_variable_settings.env_variable_used(i.name)
                if env_variable:
                    value = EnvVarParser.get_env_var(env_variable, value)
                li_settings_values.append(value)
            except TypeError:
                li_settings_values.append(
                    settings.value(key=i.name, defaultValue=i.default)
                )

        # instanciate new settings object
        options = PlgSettingsStructure(*li_settings_values)

        settings.endGroup()

        return options

    @staticmethod
    def get_value_from_key(key: str, default=None, exp_type=None):
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings value matching key
        """
        if not hasattr(PlgSettingsStructure, key):
            log_hdlr.PlgLogger.log(
                message="Bad settings key. Must be one of: {}".format(
                    ",".join(PlgSettingsStructure._fields)
                ),
                log_level=1,
            )
            return None

        settings = QgsSettings()
        settings.beginGroup(__title__)

        try:
            out_value = settings.value(key=key, defaultValue=default, type=exp_type)
        except Exception as err:
            log_hdlr.PlgLogger.log(
                message="Error occurred trying to get settings: {}.Trace: {}".format(
                    key, err
                )
            )
            out_value = None

        settings.endGroup()

        return out_value

    @classmethod
    def set_value_from_key(cls, key: str, value) -> bool:
        """Set plugin QSettings value using the key.

        :param key: QSettings key
        :type key: str
        :param value: value to set
        :type value: depending on the settings
        :return: operation status
        :rtype: bool
        """
        if not hasattr(PlgSettingsStructure, key):
            log_hdlr.PlgLogger.log(
                message="Bad settings key. Must be one of: {}".format(
                    ",".join(PlgSettingsStructure._fields)
                ),
                log_level=2,
            )
            return False

        settings = QgsSettings()
        settings.beginGroup(__title__)

        try:
            settings.setValue(key, value)
            out_value = True
        except Exception as err:
            log_hdlr.PlgLogger.log(
                message="Error occurred trying to set settings: {}.Trace: {}".format(
                    key, err
                )
            )
            out_value = False

        settings.endGroup()

        return out_value

    @classmethod
    def save_from_object(cls, plugin_settings_obj: PlgSettingsStructure):
        """Load and return plugin settings as a dictionary. \
        Useful to get user preferences across plugin logic.

        :return: plugin settings value matching key
        """
        settings = QgsSettings()
        settings.beginGroup(__title__)

        for k, v in asdict(plugin_settings_obj).items():
            cls.set_value_from_key(k, v)

        settings.endGroup()


if __name__ == "__main__":
    pass
