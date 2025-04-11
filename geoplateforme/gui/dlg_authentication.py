#! python3  # noqa: E265

"""
Authentication dialog logic.
"""

# standard
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# PyQGIS
from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog

# Plugin
from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.custom_exceptions import (
    InvalidOAuthPort,
    UnavailablePortException,
    UnavailableUserException,
)
from geoplateforme.api.user import UserRequestsManager
from geoplateforme.constants import OAUTH_DECLARED_REDIRECT_PORTS
from geoplateforme.datamodels.oauth2_configuration import OAuth2Configuration
from geoplateforme.toolbelt import PlgLogger, PlgOptionsManager
from geoplateforme.toolbelt.network_manager import NetworkRequestsManager

# only for type checking
if TYPE_CHECKING:
    from qgis.core import QgsAuthManager


class AuthenticationDialog(QDialog):
    def __init__(self, parent=None):
        """Dialog to define current geoplateforme connection as authentication config.

        :param parent: parent widget, defaults to None
        :type parent: QObject, optional
        """
        # init module and ui
        super().__init__(parent)
        uic.loadUi(Path(__file__).parent / f"{Path(__file__).stem}.ui", self)
        self.setWindowIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/User.svg")),
        )
        self.auth_manager: Optional[QgsAuthManager] = None

        # toolbelt
        self.log = PlgLogger().log
        self.ntwk_requester_blk = NetworkRequestsManager()
        self.plg_settings_mngr = PlgOptionsManager()
        self.plg_settings = self.plg_settings_mngr.get_plg_settings()

        # widgets connect
        self.btn_log_in.clicked.connect(self.connect)
        self.btn_log_in_fc.clicked.connect(self.connect_not_available)
        self.btn_log_in_pc.clicked.connect(self.connect_not_available)

    def connect_not_available(self) -> None:
        """CDisplay message for not available connect endpoint."""
        self.log(
            message=self.tr("This connect end point is currently not available "),
            log_level=Qgis.MessageLevel.Critical,
            push=True,
            duration=30,
            parent_location=self,
        )
        return

    def connect(self) -> None:
        """Check connection parameter and define current geotuileur authentication config
        if connection is valid.
        """
        # Create new authentication config and add it to manager
        self.auth_manager = QgsApplication.authManager()
        new_auth = self.plg_settings.create_auth_config()

        if not isinstance(new_auth, QgsAuthMethodConfig):
            self.log(
                message=self.tr("Error while creating authentication configuration."),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
                duration=30,
            )
            return

        auth_created = self.auth_manager.storeAuthenticationConfig(new_auth, True)
        if not auth_created[0]:
            self.log(
                message=self.tr(
                    "Error while storing authentication configuration {} in QGIS "
                    "Authentication Manager.".format(new_auth)
                ),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
                duration=30,
                parent_location=self,
            )
            return

        self.log(
            message="Credentials saved into QGIS Authentication Manager as "
            f" {new_auth.name()} ({new_auth.id()})",
            log_level=Qgis.MessageLevel.NoLevel,
        )

        # If connection valid, remove previous config and use new created config,
        # otherwise remove created config
        if self.check_connection(new_auth):
            if self.plg_settings.qgis_auth_id:
                self.auth_manager.removeAuthenticationConfig(
                    self.plg_settings.qgis_auth_id
                )
            self.plg_settings.qgis_auth_id = new_auth.id()
            self.plg_settings_mngr.save_from_object(self.plg_settings)

            # Validate dialog
            self.accept()
        else:
            self.log(
                message="Authentication configuration {} has been removed.".format(
                    new_auth.id()
                ),
                log_level=Qgis.MessageLevel.NoLevel,
                push=False,
            )
            self.auth_manager.removeAuthenticationConfig(new_auth.id())

    def check_connection(
        self,
        qgis_auth_config: QgsAuthMethodConfig,
    ) -> bool:
        """Check if connection is valid for a given QgsAuthMethodConfig.

        Display a message box with user name and last name if connection valid, or
        message with error message otherwise.

        :param qgis_auth_config: qgis authentication configuration to use
        :type QgsAuthMethodConfig: str


        :return: True if connection is valid for qgis_auth_config, False otherwise
        :rtype: bool
        """

        res = True

        # Check connection to API by getting token user information
        try:
            manager = UserRequestsManager()
            manager.plg_settings.qgis_auth_id = qgis_auth_config.id()

            # check if an acceptable port is available
            self.get_available_redirect_port(qgis_auth_config)
            self.auth_manager.storeAuthenticationConfig(qgis_auth_config, True)

            # try to get authenticated user informations
            user = manager.get_user()
            self.log(
                message=self.tr("Welcome {} !".format(user.email)),
                log_level=Qgis.MessageLevel.Success,
                push=True,
                duration=5,
            )

        except UnavailableUserException as exc:
            self.log(
                message=self.tr("Authentication failed. Trace: {}".format(exc)),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
                duration=30,
                parent_location=self,
            )
            res = False

        except UnavailablePortException:
            self.log(
                self.tr(
                    "None of the usable port {} is available. Please see requirements."
                ).format(OAUTH_DECLARED_REDIRECT_PORTS),
                log_level=Qgis.MessageLevel.Critical,
                push=True,
                duration=30,
                parent_location=self,
            )
            res = False

            self.qgrp_requirements.setCollapsed(False)

        return res

    def get_available_redirect_port(
        self,
        qgis_auth_config: QgsAuthMethodConfig,
    ) -> bool:
        """Check if one of declared oAuth port is available for callback redirection.

        :param qgis_auth_config: qgis authentication configuration to use
        :type QgsAuthMethodConfig: str

        :return: True if port is available, False otherwise
        :rtype: bool
        """
        oauth2cfg = OAuth2Configuration.from_config_map(qgis_auth_config.configMap())

        # check if port is in declared ports
        if oauth2cfg.redirectPort not in OAUTH_DECLARED_REDIRECT_PORTS:
            self.log(
                InvalidOAuthPort(
                    "Port {} is not in the list of declared ports: {}. It could lead to "
                    "unexpect behavior.".format(
                        oauth2cfg.redirectPort,
                        OAUTH_DECLARED_REDIRECT_PORTS,
                    )
                ),
                log_level=Qgis.MessageLevel.Warning,
                parent_location=self,
            )

        # if port is available
        if self.ntwk_requester_blk.is_port_available(
            port=oauth2cfg.redirectPort,
        ):
            self.log(
                message=self.tr(
                    "Port {} is available and will be used to perform oAuth2 related "
                    "operations.".format(
                        oauth2cfg.redirectPort,
                    )
                ),
                push=True,
                duration=5,
                parent_location=self,
            )
            return True

        # if port is not available, parse the list of declared ports and check if one
        # of them is available
        self.log(
            message=self.tr(
                "Port {} is not available. Trying another port among declared ones: {}.".format(
                    oauth2cfg.redirectPort,
                    OAUTH_DECLARED_REDIRECT_PORTS,
                )
            ),
            log_level=Qgis.MessageLevel.Warning,
            push=True,
            duration=5,
            parent_location=self,
        )
        for possible_port in OAUTH_DECLARED_REDIRECT_PORTS:
            if possible_port == oauth2cfg.redirectPort:
                self.log(
                    message="Port {} has already been tested. Skipping.".format(
                        possible_port
                    ),
                    log_level=Qgis.MessageLevel.NoLevel,
                )
                continue
            # check if the port is available
            if self.ntwk_requester_blk.is_port_available(
                port=possible_port,
            ):
                # if available, set it in the configuration
                oauth2cfg.redirectPort = possible_port
                qgis_auth_config.setConfigMap(
                    {"oauth2config": oauth2cfg.as_qgis_str_config_map()},
                )
                return self.get_available_redirect_port(
                    qgis_auth_config,
                )

        # no more port available
        raise UnavailablePortException
