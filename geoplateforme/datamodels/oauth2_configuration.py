# standard
import json
from dataclasses import asdict, dataclass, field
from os import getenv
from pathlib import Path
from typing import Optional

# PyQGIS
from qgis.core import Qgis

# plugin
import geoplateforme.toolbelt.log_handler as log_hdlr
from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.custom_exceptions import InvalidOAuthConfiguration

# -- GLOBALS --

# Required fields for a QGIS oAuth2 configuration
QGS_REQUIRED_FIELDS = [
    "accessMethod",
    "clientId",
    "clientSecret",
    "configType",
    "grantFlow",
    "persistToken",
    "redirectPort",
    "redirectUrl",
    "requestTimeout",
    "requestUrl",
    "scope",
    "tokenUrl",
    "version",
]


@dataclass
class OAuth2Configuration:
    """oAuth2 configuration object."""

    accessMethod: int = 0
    apiKey: str = ""
    clientId: str = ""
    clientSecret: str = ""
    configType: int = 1
    customHeader: str = ""
    description: str = (
        "Authentication related to the Géoplateforme plugin to give access to cartes.gouv.fr "
        "access your community, publish your data as services hosted on the IGN Geoplatform."
    )
    grantFlow: int = 0
    id: str = ""
    name: str = "geoplateforme_plugin_cfg"
    objectName: str = ""
    password: str = ""
    persistToken: bool = True
    queryPairs: dict = field(default_factory=dict)
    redirectPort: int = 7070
    redirectUrl: str = "callback"
    refreshTokenUrl: str = ""
    requestTimeout: int = 30
    requestUrl: str = (
        "https://sso.geopf.fr/realms/geoplateforme/protocol/openid-connect/auth"
    )
    scope: str = ""
    tokenUrl: str = (
        "https://sso.geopf.fr/realms/geoplateforme/protocol/openid-connect/token"
    )
    username: str = ""
    version: int = 1

    def as_qgis_str_config_map(self) -> str:
        """Convert the OAuth2Configuration instance to a string representation of a
        dictionary containing only the required fields for the QGIS configuration.

        :return: string representation of the configuration with only required fields.
        :rtype: str
        """
        oauth_config_dict = asdict(self)
        keys_to_remove = [
            key for key in oauth_config_dict if key not in QGS_REQUIRED_FIELDS
        ]

        for key in keys_to_remove:
            oauth_config_dict.pop(key)

        log_hdlr.PlgLogger.log(
            message="oAuth2 configuration converted as str to comply with QGIS "
            "Authentication manager.",
            log_level=Qgis.MessageLevel.Success,
            push=False,
        )

        # ' not supported by pyqgis, replace by "
        oauth_config_str = str(oauth_config_dict).replace("'", '"')

        # replace also boolean str
        oauth_config_str = oauth_config_str.replace("False", "false").replace(
            "True", "true"
        )

        return oauth_config_str

    @classmethod
    def from_config_map(
        cls, qgis_config_map: dict[str, str]
    ) -> Optional["OAuth2Configuration"]:
        """Creates an OAuth2Configuration instance from a QGIS configuration map.

        :param qgis_config_map: QGIS configuration map containing the OAuth2
        configuration.
        :type qgis_config_map: dict

        :raises InvalidOAuthConfiguration: when config map is not JSON compliant

        :return: instance of OAuth2Configuration populated with the data from the
        configuration map.
        :rtype: OAuth2Configuration
        """
        #  load configuration in json
        try:
            # make config map compliant with JSON format
            cfg_map = (
                qgis_config_map.get("oauth2config")
                .replace("False", "false")
                .replace("True", "true")
                .replace("'", '"')
                .replace("None", "null")
            )
            cfg_json = json.loads(cfg_map)
        except json.decoder.JSONDecodeError as err:
            err_msg = (
                "Configuration map ({}) could not be loaded as JSON. Error: {}".format(
                    qgis_config_map, err
                )
            )
            log_hdlr.PlgLogger.log(
                message=err_msg,
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            raise InvalidOAuthConfiguration(err_msg)

        # check if the config map is compliant with the expected structure
        if not cls.is_json_compliant(cfg_json):
            log_hdlr.PlgLogger.log(
                message="Configuration map does not comply with the expected "
                "structure. Please check your configuration.",
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return

        log_hdlr.PlgLogger.log(
            message="oAuth2 configuration loaded from QGIS config map.",
            log_level=Qgis.MessageLevel.NoLevel,
            push=False,
        )

        return cls(**json.loads(cfg_map))

    @classmethod
    def from_json(
        cls, json_filepath: Optional[Path] = None
    ) -> Optional["OAuth2Configuration"]:
        """Loads an OAuth2Configuration instance from the given JSON file path.

        :param json_filepath: Path to the JSON file containing the configuration.
        :type json_filepath: Path

        :return: instance of OAuth2Configuration populated with the data from the JSON file.
        :rtype: OAuth2Configuration
        """
        # if no path is provided, get the default one
        if json_filepath is None:
            json_filepath = cls.get_json_path()

        # if the default path is not found, return right now
        if not isinstance(json_filepath, Path):
            return

        # if the file exist, try load the JSON data
        try:
            with json_filepath.open(mode="r", encoding="utf8") as my_json:
                json_data = json.load(my_json)
            log_hdlr.PlgLogger.log(
                message="JSON file ({}) read and data loaded successfully.".format(
                    json_filepath
                ),
                log_level=Qgis.MessageLevel.NoLevel,
                push=False,
            )
        except json.decoder.JSONDecodeError as err:
            log_hdlr.PlgLogger.log(
                message="JSON file ({}) could not be read. Error: {}".format(
                    json_filepath, err
                ),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return

        # check if the JSON data is compliant with the expected structure
        if not cls.is_json_compliant(json_data):
            return

        log_hdlr.PlgLogger.log(
            f"oAuth2 configuration loaded from {json_filepath}.",
            log_level=Qgis.MessageLevel.NoLevel,
        )

        return cls(
            **json_data,
        )

    @classmethod
    def get_json_path(cls) -> Optional[Path]:
        """Return path to the oAuth2 JSON filepath.

        :return: path to the JSON file containing the configuration.
        :rtype: Optional[Path]
        """
        json_config_filepath = Path(
            getenv(
                "PLUGIN_GEOPLATEFORME_OAUTH2_CONFIG",
                DIR_PLUGIN_ROOT.joinpath("auth/oauth2_config.json"),
            )
        )

        if not json_config_filepath.exists():
            log_hdlr.PlgLogger.log(
                message="The configuration file can't be found: {}".format(
                    json_config_filepath
                ),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return

        return json_config_filepath.resolve()

    @classmethod
    def is_json_compliant(cls, json_data: dict) -> bool:
        """Check whether the JSON configuration at the given path contains all the
        required keys for the OAuth2Configuration dataclass.

        :param json_data: Path to the JSON file containing the configuration.
        :type json_data: dict

        :return: True if the JSON data is compliant with the expected structure, False
        otherwise.
        :rtype: bool
        """
        missing_fields = [
            field for field in QGS_REQUIRED_FIELDS if field not in json_data
        ]

        if missing_fields:
            log_hdlr.PlgLogger.log(
                message="Data does not comply with the expected oAuth structure. "
                "Following fields are missing: {}.".format(missing_fields),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
            )
            return False

        log_hdlr.PlgLogger.log(
            message="JSON data is compliant with the expected structure.",
            log_level=Qgis.MessageLevel.Success,
            push=False,
        )

        return True
