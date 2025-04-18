#! python3  # noqa: E265

"""
Main plugin module.
"""

# standard
from functools import partial
from pathlib import Path
from typing import Optional

# PyQGIS
from qgis.core import QgsApplication, QgsSettings
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

# project
from geoplateforme.__about__ import DIR_PLUGIN_ROOT, __title__, __uri_homepage__
from geoplateforme.gui.dashboard.dlg_dashboard import DashboardDialog
from geoplateforme.gui.dlg_authentication import AuthenticationDialog
from geoplateforme.gui.dlg_settings import PlgOptionsFactory
from geoplateforme.gui.publication_creation.wzd_publication_creation import (
    PublicationFormCreation,
)
from geoplateforme.gui.storage.dlg_storage_report import StorageReportDialog
from geoplateforme.gui.tile_creation.wzd_tile_creation import TileCreationWizard
from geoplateforme.gui.upload_creation.wzd_upload_creation import UploadCreationWizard
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

        # initialize the locale
        self.locale: str = QgsSettings().value("locale/userLocale", QLocale().name())[
            0:2
        ]
        locale_path: Path = (
            DIR_PLUGIN_ROOT / f"resources/i18n/{__title__.lower()}_{self.locale}.qm"
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

        self.toolbar = None
        self.dlg_dashboard = None
        self.dlg_storage_report = None

        self.action_authentication = None
        self.action_dashboard = None
        self.action_storage_report = None
        self.action_import = None
        self.action_tile_create = None
        self.action_publication = None

        self.btn_autentification = None
        self.btn_import = None
        self.btn_configuration = None
        self.btn_publication = None

        self.import_wizard = None
        self.tile_creation_wizard = None
        self.publication_wizard = None

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

        # Storage report
        self.action_storage_report = QAction(
            QIcon(QgsApplication.iconPath("mIconAuxiliaryStorage.svg")),
            self.tr("Storage report"),
            self.iface.mainWindow(),
        )
        self.action_storage_report.triggered.connect(self.display_storage_report)

        # Import
        self.action_import = QAction(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Deposer.png")),
            self.tr("Create a new upload"),
            self.iface.mainWindow(),
        )
        self.action_import.triggered.connect(self.import_data)

        # Tile creation
        self.action_tile_create = QAction(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Tuile@1x.png")),
            self.tr("Tile creation"),
            self.iface.mainWindow(),
        )
        self.action_tile_create.triggered.connect(self.tile_creation)

        # Publication
        self.action_publication = QAction(
            QIcon(
                str(
                    DIR_PLUGIN_ROOT / "resources" / "images" / "icons" / "Publie@2x.png"
                )
            ),
            self.tr("Publication"),
            self.iface.mainWindow(),
        )
        self.action_publication.triggered.connect(self.publication)

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

        # -- Menu
        self.iface.addPluginToWebMenu(__title__, self.action_authentication)
        self.iface.addPluginToWebMenu(__title__, self.action_dashboard)
        self.iface.addPluginToWebMenu(__title__, self.action_storage_report)
        self.iface.addPluginToWebMenu(__title__, self.action_import)
        self.iface.addPluginToWebMenu(__title__, self.action_tile_create)
        self.iface.addPluginToWebMenu(__title__, self.action_publication)
        self.iface.addPluginToWebMenu(__title__, self.action_settings)
        self.iface.addPluginToWebMenu(__title__, self.action_help)

        # -- Toolbar
        self.toolbar = QToolBar("GeoplateformeToolbar")
        self.iface.addToolBar(self.toolbar)
        self.toolbar.addAction(self.action_authentication)
        self.toolbar.addAction(self.action_dashboard)
        self.toolbar.addAction(self.action_storage_report)
        self.toolbar.addAction(self.action_import)
        self.toolbar.addAction(self.action_tile_create)
        self.toolbar.addAction(self.action_publication)
        self._update_actions_availability()

        # -- Processings
        self.initProcessing()

    def initProcessing(self):
        self.provider = GeoplateformeProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Cleans up when plugin is disabled/uninstalled."""
        # -- Clean up menu
        self.iface.removePluginWebMenu(__title__, self.action_authentication)
        self.iface.removePluginWebMenu(__title__, self.action_dashboard)
        self.iface.removePluginWebMenu(__title__, self.action_storage_report)
        self.iface.removePluginWebMenu(__title__, self.action_import)
        self.iface.removePluginWebMenu(__title__, self.action_tile_create)
        self.iface.removePluginWebMenu(__title__, self.action_publication)
        self.iface.removePluginWebMenu(__title__, self.action_help)
        self.iface.removePluginWebMenu(__title__, self.action_settings)

        # remove toolbar :
        self.toolbar.deleteLater()

        # -- Clean up preferences panel in QGIS settings
        self.iface.unregisterOptionsWidgetFactory(self.options_factory)

        # -- Unregister processing
        QgsApplication.processingRegistry().removeProvider(self.provider)

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

    def tile_creation(self) -> None:
        """
        Open tile creation Wizard

        """
        if self.tile_creation_wizard is None:
            self.tile_creation_wizard = TileCreationWizard(self.iface.mainWindow())
            self.tile_creation_wizard.finished.connect(self._del_tile_creation_wizard)
        self.tile_creation_wizard.show()

    def publication(self):
        """
        Open tile creation Wizard

        """
        if self.publication_wizard is None:
            self.publication_wizard = PublicationFormCreation(self.iface.mainWindow())
            self.publication_wizard.finished.connect(self._del_tile_publication_wizard)
        self.publication_wizard.show()

    def import_data(self):
        """
        Open import data Wizard

        """
        if self.import_wizard is None:
            self.import_wizard = UploadCreationWizard(self.iface.mainWindow())
            self.import_wizard.finished.connect(self._del_import_wizard)
        self.import_wizard.show()

    def _del_import_wizard(self) -> None:
        """
        Delete import wizard

        """
        if self.import_wizard is not None:
            self.import_wizard.deleteLater()
            self.import_wizard = None

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
        if self.dlg_auth is None:
            self.dlg_auth = AuthenticationDialog()

        self.dlg_auth.finished.connect(self._update_actions_availability)
        self.dlg_auth.show()

    def _update_actions_availability(self) -> None:
        """
        Update actions availability if user is connected or not

        """
        plg_settings = self.plg_settings.get_plg_settings()
        enabled = plg_settings.qgis_auth_id is not None

        self.action_dashboard.setEnabled(enabled)
        self.action_storage_report.setEnabled(False)
        self.action_import.setEnabled(False)
        self.action_tile_create.setEnabled(False)
        self.action_publication.setEnabled(False)

    def display_dashboard(self) -> None:
        """
        Display dashboard dialog

        """
        if self.dlg_dashboard is None:
            self.dlg_dashboard = DashboardDialog(self.iface.mainWindow())

        self.dlg_dashboard.refresh()
        self.dlg_dashboard.show()

    def display_storage_report(self) -> None:
        """
        Display storage report dialog

        """
        if self.dlg_storage_report is None:
            self.dlg_storage_report = StorageReportDialog(self.iface.mainWindow())

        self.dlg_storage_report.refresh()
        self.dlg_storage_report.show()
