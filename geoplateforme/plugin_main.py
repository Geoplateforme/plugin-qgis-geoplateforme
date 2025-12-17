#! python3  # noqa: E265

"""
Main plugin module.
"""

# standard
from functools import partial
from pathlib import Path
from typing import Optional

# PyQGIS
from qgis.core import Qgis, QgsApplication, QgsSettings
from qgis.gui import QgisInterface, QgsGui
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar
from qgis.utils import plugins

# project
from geoplateforme.__about__ import (
    DIR_PLUGIN_ROOT,
    __title__,
    __uri_homepage__,
    __uri_tracker__,
)
from geoplateforme.api.custom_exceptions import UnavailableUserException
from geoplateforme.constants import GPF_PLUGIN_LIST
from geoplateforme.gui.dashboard.mw_dashboard import DashboardWindow
from geoplateforme.gui.dlg_authentication import AuthenticationDialog
from geoplateforme.gui.dlg_settings import PlgOptionsFactory
from geoplateforme.gui.provider.provider_gpf import ProviderGPF
from geoplateforme.gui.storage.dlg_storage_report import StorageReportDialog
from geoplateforme.gui.user.dlg_user import UserDialog
from geoplateforme.gui.user_keys.dlg_user_keys import UserKeysDialog
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.toolbelt import PlgLogger, PlgOptionsManager


class GeoplateformePlugin:
    def __init__(self, iface: QgisInterface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class which \
        provides the hook by which you can manipulate the QGIS application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.log = PlgLogger().log
        self.provider = None
        self.provider_gpf = None

        # initialize the locale
        self.locale: str = QgsSettings().value("locale/userLocale", QLocale().name())[
            0:2
        ]
        locale_path: Path = (
            DIR_PLUGIN_ROOT / f"resources/i18n/geoplateforme_{self.locale}.qm"
        )
        self.log(message=f"Translation: {self.locale}, {locale_path}", log_level=4)
        if locale_path.exists():
            self.translator = QTranslator()
            self.translator.load(str(locale_path.resolve()))
            QCoreApplication.installTranslator(self.translator)

        # plugin settings
        self.plg_settings = PlgOptionsManager()

        self.options_factory = None
        self.action_help = None
        self.action_settings = None
        self.action_report_issue = None

        self.toolbar = None
        self.mw_dashboard = None
        self.dlg_user_keys = None
        self.dlg_storage_report = None

        self.action_authentication = None
        self.action_dashboard = None
        self.action_user_keys = None
        self.action_storage_report = None

        self.btn_autentification = None
        self.btn_import = None
        self.btn_configuration = None
        self.btn_publication = None

        self.import_wizard = None
        self.tile_creation_wizard = None
        self.publication_wizard = None

        self.external_plugin_actions = []

        self.dlg_auth: Optional[AuthenticationDialog] = None

    def initGui(self):
        """Set up plugin UI elements."""

        # settings page within the QGIS preferences menu
        self.options_factory = PlgOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        # -- Actions
        # Login
        self.action_authentication = QAction(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/User.svg")),
            self.tr("Login"),
            self.iface.mainWindow(),
        )
        self.action_authentication.triggered.connect(self.authentication)

        # Dashboard
        self.action_dashboard = QAction(
            QIcon(
                str(
                    DIR_PLUGIN_ROOT
                    / "resources"
                    / "images"
                    / "datastore"
                    / "bac-a-sable.svg"
                )
            ),
            self.tr("Dashboard"),
            self.iface.mainWindow(),
        )
        self.action_dashboard.triggered.connect(self.display_dashboard)

        # User keys
        self.action_user_keys = QAction(
            QIcon(":images/themes/default/locked.svg"),
            self.tr("Access keys"),
            self.iface.mainWindow(),
        )
        self.action_user_keys.triggered.connect(self.user_keys)

        # Storage report
        self.action_storage_report = QAction(
            QIcon(QgsApplication.iconPath("mIconAuxiliaryStorage.svg")),
            self.tr("Storage report"),
            self.iface.mainWindow(),
        )
        self.action_storage_report.triggered.connect(self.display_storage_report)

        # Help
        self.action_help = QAction(
            QIcon(":/images/themes/default/mActionHelpContents.svg"),
            self.tr("Help"),
            self.iface.mainWindow(),
        )
        self.action_help.triggered.connect(
            partial(QDesktopServices.openUrl, QUrl(__uri_homepage__))
        )

        # Settings
        self.action_settings = QAction(
            QgsApplication.getThemeIcon("console/iconSettingsConsole.svg"),
            self.tr("Settings"),
            self.iface.mainWindow(),
        )
        self.action_settings.triggered.connect(
            lambda: self.iface.showOptionsDialog(
                currentPage="mOptionsPage{}".format(__title__)
            )
        )

        # Issue report
        self.action_report_issue = QAction(
            QgsApplication.getThemeIcon("console/iconSyntaxErrorConsole.svg"),
            self.tr("Report issue"),
            self.iface.mainWindow(),
        )

        self.action_report_issue.triggered.connect(
            partial(
                QDesktopServices.openUrl,
                QUrl(
                    f"{__uri_tracker__}new?template=10_bug_report.yml&assignees=IGNF-Xavier"
                ),
            )
        )

        # -- Menu
        self.iface.addPluginToMenu(__title__, self.action_authentication)
        self.iface.addPluginToMenu(__title__, self.action_dashboard)
        self.iface.addPluginToMenu(__title__, self.action_user_keys)
        self.iface.addPluginToMenu(__title__, self.action_storage_report)
        self.iface.addPluginToMenu(__title__, self.action_settings)
        self.iface.addPluginToMenu(__title__, self.action_help)
        self.iface.addPluginToMenu(__title__, self.action_report_issue)

        # -- Toolbar
        self.toolbar = QToolBar("GeoplateformeToolbar")
        self.iface.addToolBar(self.toolbar)
        self.toolbar.addAction(self.action_authentication)
        self.toolbar.addAction(self.action_dashboard)
        self.toolbar.addAction(self.action_user_keys)
        self.toolbar.addAction(self.action_storage_report)
        self._update_actions_availability()

        # -- Provider
        self.provider_gpf = ProviderGPF(self.iface)
        QgsGui.sourceSelectProviderRegistry().addProvider(self.provider_gpf)

        # Connect to settings change in case of reset
        instance_gui = QgsGui.instance()
        instance_gui.optionsChanged.connect(self._update_actions_availability)

        # -- Processings
        self.initProcessing()

        # Add actions from GPF plugins
        self.add_gpf_plugins_actions()

    def initProcessing(self):
        self.provider = GeoplateformeProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def add_gpf_plugins_actions(self) -> None:
        """Add action for gpf plugin"""

        separator_added = False

        # Get plugin instance
        for plugin in GPF_PLUGIN_LIST:
            if plugin not in plugins:
                self.log(
                    "Plugin {} not available. Can't add actions for plugin.".format(
                        plugin
                    ),
                    log_level=Qgis.MessageLevel.Info,
                    push=False,
                )
            else:
                plugin_instance = plugins[plugin]
                actions_list_fct = getattr(
                    plugin_instance, "create_gpf_plugins_actions", None
                )
                if not callable(actions_list_fct):
                    self.log(
                        "Method create_gpf_plugins_actions not available for plugin {}. Can't add actions for plugin.".format(
                            plugin
                        ),
                        log_level=Qgis.MessageLevel.Info,
                        push=False,
                    )
                else:
                    try:
                        actions_list = plugin_instance.create_gpf_plugins_actions(
                            self.iface.mainWindow()
                        )
                        if not separator_added:
                            sep_action = QAction(self.iface.mainWindow())
                            sep_action.setText(self.tr("3rd party extensions"))
                            sep_action.setSeparator(True)
                            self.external_plugin_actions.append(sep_action)
                            self.iface.addPluginToMenu(__title__, sep_action)
                            separator_added = True
                        for action in actions_list:
                            if isinstance(action, QAction):
                                self.external_plugin_actions.append(action)
                                self.iface.addPluginToMenu(__title__, action)
                            else:
                                self.log(
                                    "Only QAction should be returned by `create_gpf_plugins_actions` for plugin : {}.".format(
                                        plugin
                                    ),
                                    log_level=Qgis.MessageLevel.Info,
                                    push=False,
                                )
                    except Exception as exc:
                        self.log(
                            "Exception raised by external plugin {} when calling `create_gpf_plugins_actions` : {}.".format(
                                plugin, exc
                            ),
                            log_level=Qgis.MessageLevel.Info,
                            push=False,
                        )

    def unload(self):
        """Cleans up when plugin is disabled/uninstalled."""
        # -- Clean up menu
        self.iface.removePluginMenu(__title__, self.action_authentication)
        self.iface.removePluginMenu(__title__, self.action_dashboard)
        self.iface.removePluginMenu(__title__, self.action_user_keys)
        self.iface.removePluginMenu(__title__, self.action_storage_report)
        self.iface.removePluginMenu(__title__, self.action_help)
        self.iface.removePluginMenu(__title__, self.action_report_issue)
        self.iface.removePluginMenu(__title__, self.action_settings)

        for action in self.external_plugin_actions:
            self.iface.removePluginMenu(__title__, action)

        # remove toolbar :
        self.toolbar.deleteLater()

        # -- Clean up preferences panel in QGIS settings
        self.iface.unregisterOptionsWidgetFactory(self.options_factory)

        # -- Unregister processing
        QgsApplication.processingRegistry().removeProvider(self.provider)

        # -- Unregister datasource provider
        if self.provider_gpf:
            QgsGui.sourceSelectProviderRegistry().removeProvider(self.provider_gpf)

        # remove actions
        del self.action_settings
        del self.action_help

    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def _del_tile_creation_wizard(self) -> None:
        """
        Delete tile creation wizard

        """
        if self.tile_creation_wizard is not None:
            self.tile_creation_wizard.deleteLater()
            self.tile_creation_wizard = None

    def _del_tile_publication_wizard(self) -> None:
        """
        Delete tile publication wizard

        """
        if self.publication_wizard is not None:
            self.publication_wizard.deleteLater()
            self.publication_wizard = None

    def authentication(self) -> None:
        """Display authentication dialog to initiate log-in pairing on GitLab."""
        connection_valid = False
        if self.plg_settings.get_plg_settings().qgis_auth_id:
            try:
                dlg_user = UserDialog(self.iface.mainWindow())
                dlg_user.exec()
                connection_valid = True
            except UnavailableUserException:
                self.plg_settings.disconnect()

        if not connection_valid:
            if self.dlg_auth is None:
                self.dlg_auth = AuthenticationDialog()
                self.dlg_auth.finished.connect(self._update_actions_availability)
            self.dlg_auth.show()
        else:
            self._update_actions_availability()

    def _update_actions_availability(self) -> None:
        """
        Update actions availability if user is connected or not

        """
        plg_settings = self.plg_settings.get_plg_settings()
        enabled = (
            plg_settings.qgis_auth_id is not None and plg_settings.qgis_auth_id != ""
        )
        self.action_dashboard.setEnabled(enabled)
        self.action_user_keys.setEnabled(enabled)
        self.action_storage_report.setEnabled(False)

        # Close dashboard if connection is not available
        if not enabled:
            if self.mw_dashboard is not None:
                self.mw_dashboard.close()
                del self.mw_dashboard
                self.mw_dashboard = None

    def user_keys(self) -> None:
        if self.dlg_user_keys is None:
            self.dlg_user_keys = UserKeysDialog(self.iface.mainWindow())
        self.dlg_user_keys.refresh()
        self.dlg_user_keys.show()

    def display_dashboard(self) -> None:
        """
        Display dashboard dialog

        """
        if self.mw_dashboard is None:
            self.mw_dashboard = DashboardWindow(self.iface.mainWindow())
            self.mw_dashboard.refresh()
        self.mw_dashboard.show()

    def display_storage_report(self) -> None:
        """
        Display storage report dialog

        """
        if self.dlg_storage_report is None:
            self.dlg_storage_report = StorageReportDialog(self.iface.mainWindow())

        self.dlg_storage_report.refresh()
        self.dlg_storage_report.show()
