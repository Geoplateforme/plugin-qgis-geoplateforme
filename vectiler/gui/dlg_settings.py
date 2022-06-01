#! python3  # noqa: E265

"""
    Plugin settings form integrated into QGIS 'Options' menu.
"""

# standard
import json
from functools import partial
from pathlib import Path

# PyQGIS
from qgis.core import QgsApplication
from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory
from qgis.PyQt import uic
from qgis.PyQt.Qt import QUrl
from qgis.PyQt.QtCore import QByteArray, QCoreApplication
from qgis.PyQt.QtGui import QDesktopServices, QIcon

# project
from vectiler.__about__ import (
    DIR_PLUGIN_ROOT,
    __title__,
    __uri_homepage__,
    __uri_tracker__,
    __version__,
)
from vectiler.api.client import NetworkRequestsManager
from vectiler.toolbelt import PlgLogger, PlgOptionsManager
from vectiler.toolbelt.preferences import PlgSettingsStructure

# ############################################################################
# ########## Globals ###############
# ##################################

FORM_CLASS, _ = uic.loadUiType(
    Path(__file__).parent / "{}.ui".format(Path(__file__).stem)
)


# ############################################################################
# ########## Classes ###############
# ##################################


class ConfigOptionsPage(FORM_CLASS, QgsOptionsPageWidget):
    """Settings form embedded into QGIS 'options' menu."""

    def __init__(self, parent):
        super().__init__(parent)
        self.log = PlgLogger().log
        self.network_requests_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager()
        self.setupUi(self)
        self.setObjectName("mOptionsPage{}".format(__title__))

        # header
        self.lbl_title.setText(f"{__title__} - Version {__version__}")

        # customization
        self.btn_check_connection.pressed.connect(self.check_connection)
        self.btn_check_connection.setIcon(
            QIcon(":/images/themes/default/repositoryDisabled.svg")
        )

        self.btn_help.setIcon(QIcon(":/images/themes/default/mActionHelpContents.svg"))
        self.btn_help.pressed.connect(
            partial(QDesktopServices.openUrl, QUrl(__uri_homepage__))
        )

        self.btn_report.setIcon(
            QIcon(":images/themes/default/console/iconSyntaxErrorConsole.svg")
        )
        self.btn_report.pressed.connect(
            partial(QDesktopServices.openUrl, QUrl(f"{__uri_tracker__}new/"))
        )

        # load previously saved settings
        self.load_settings()

    def apply(self):
        """Called to permanently apply the settings shown in the options page (e.g. \
        save them to QgsSettings objects). This is usually called when the options \
        dialog is accepted."""
        new_settings = PlgSettingsStructure(
            # global
            debug_mode=self.opt_debug.isChecked(),
            version=__version__,
            # network and authentication
            url_geotuileur=self.lne_url_geotuileur.text(),
            url_service_vt=self.lne_url_service_vt.text(),
            url_auth=self.lne_url_auth.text(),
            auth_realm=self.lne_auth_realm.text(),
            auth_client_id=self.lne_auth_client_id.text(),
            qgis_auth_id=self.cbb_auth_config_select.configId(),
        )

        # dump new settings into QgsSettings
        self.plg_settings.save_from_object(new_settings)

        if __debug__:
            self.log(
                message="DEBUG - Settings successfully saved.",
                log_level=4,
            )

    def load_settings(self):
        """Load options from QgsSettings into UI form."""
        settings = self.plg_settings.get_plg_settings()

        # global
        self.opt_debug.setChecked(settings.debug_mode)
        self.lbl_version_saved_value.setText(settings.version)

        # network and authentication
        self.lne_url_geotuileur.setText(settings.url_geotuileur)
        self.lne_url_service_vt.setText(settings.url_service_vt)
        self.lne_url_auth.setText(settings.url_auth)
        self.lne_auth_realm.setText(settings.auth_realm)
        self.lne_auth_client_id.setText(settings.auth_client_id)
        self.cbb_auth_config_select.setConfigId(settings.qgis_auth_id)

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    # -- LOGIC
    def check_connection(self):
        """Check connection to API."""
        check = self.network_requests_manager.get_api_token()
        if not isinstance(check, (dict, QByteArray, bytes)):
            self.btn_check_connection.setIcon(
                QIcon(":/images/themes/default/repositoryUnavailable.svg")
            )
            self.btn_check_connection.setToolTip(check)
            return
        else:
            self.btn_check_connection.setIcon(
                QIcon(":/images/themes/default/repositoryConnected.svg")
            )
            self.btn_check_connection.setToolTip("Connection OK")

        # decode token as dict
        data = json.loads(check.data().decode("utf-8"))
        if not isinstance(data, dict):
            self.log(
                message=f"ERROR - Invalid token data received. Expected dict, not {type(data)}",
                log_level=2,
                push=True,
            )
        else:
            self.log(data, log_level=4)


class PlgOptionsFactory(QgsOptionsWidgetFactory):
    """Factory for options widget."""

    def __init__(self):
        super().__init__()

    def icon(self) -> QIcon:
        return QIcon(str(DIR_PLUGIN_ROOT / "resources/images/default_icon.png"))

    def createWidget(self, parent) -> ConfigOptionsPage:
        return ConfigOptionsPage(parent)

    def title(self) -> str:
        return __title__

    def helpId(self) -> str:
        return __uri_homepage__
