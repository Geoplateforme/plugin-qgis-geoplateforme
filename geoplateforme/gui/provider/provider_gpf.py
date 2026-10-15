from qgis.core import QgsProviderRegistry
from qgis.gui import QgsSourceSelectProvider
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.gui.provider.provider_dialog import ProviderDialog


class ProviderGPF(QgsSourceSelectProvider):
    """
    Provider pour les données de Bordeaux Métropole
    """

    def __init__(self, iface):
        super().__init__()

        self.iface = iface
        self.icon = QIcon(str(DIR_PLUGIN_ROOT) + "/resources/images/logo_IGN.png")
        self.name = "Données Géoplateforme"
        self.ordering = 0
        self.providerKey = ""
        self.text = "Données Géoplateforme"
        self.tooltip = "Données issue de la Geoplateforme de l'IGN"

    def createDataSourceWidget(
        self,
        parent=None,
        fl=Qt.WindowType.Widget,
        widgetMode=QgsProviderRegistry.WidgetMode.Embedded,
    ):
        return ProviderDialog(self.iface)

    def icon(self):
        return self.icon

    def name(self):
        return self.name

    def ordering(self):
        return self.ordering

    def providerKey(self):
        return self.providerKey

    def text(self):
        return self.text

    def tooltip(self):
        return self.tooltip
