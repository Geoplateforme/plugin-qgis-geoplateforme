import json
import logging
import os

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsVectorTileLayer
from qgis.gui import QgsAbstractDataSourceWidget
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialogButtonBox

from geoplateforme.gui.provider.capabilities_reader import (
    read_tms_layer_capabilities,
    read_wmts_layer_capabilities,
)
from geoplateforme.gui.provider.choose_authentication_dialog import (
    ChooseAuthenticationDialog,
)
from geoplateforme.gui.provider.mdl_search_result import SearchResultModel
from geoplateforme.gui.provider.wdg_range_slider import QtRangeSlider
from geoplateforme.toolbelt import PlgLogger

logger = logging.getLogger(__name__)


class ProviderDialog(QgsAbstractDataSourceWidget):
    """
    Boite de dialogue de sélection des couches
    """

    def __init__(self, iface):
        """
        QgsAbstractDataSourceWidget to display IGN data provider

        Args:
            iface: iface
        """
        super(ProviderDialog, self).__init__()

        self.iface = iface
        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "provider_dialog.ui"),
            self,
        )

        self.log = PlgLogger().log

        self.rs_production_year = QtRangeSlider(self, 1800, 2200, 1900, 2100)
        self.rs_production_year.left_thumb_value_changed.connect(
            lambda x: self.lb_py_min.setText(str(x))
        )
        self.rs_production_year.right_thumb_value_changed.connect(
            lambda x: self.lb_py_max.setText(str(x))
        )
        self.layout_advanced_search.addWidget(self.rs_production_year, 6, 6)

        self.cb_open.addItems(["True", "False"])
        self.cb_open.setCurrentIndex(-1)
        self.cb_type.addItems(
            [
                "WFS",
                "WMS",
                "WMTS",
                "TMS",
            ]
        )
        self.cb_type.setCurrentIndex(-1)

        self.mdl_search_result = SearchResultModel()
        self.tbv_results.setModel(self.mdl_search_result)
        self.tbv_results.verticalHeader().setVisible(False)
        self.tbv_results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_results.pressed.connect(self._item_clicked)
        self.tbv_results.doubleClicked.connect(self._add_layer)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setText("Ajouter")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

        self.tw_search.currentChanged.connect(self._clear_search)

        self.le_search.textChanged.connect(self._simple_search)
        self.btn_search.clicked.connect(self._advanced_search)
        self.btn_clear_search.clicked.connect(self._clear_search)
        self.buttonBox.clicked.connect(self.onAccept)

    def _clear_search(self):
        """clear search results"""
        self.le_search.clear()

        self.le_title.clear()
        self.le_layername.clear()
        self.le_theme.clear()
        self.le_producer.clear()
        self.le_keywords.clear()
        self.cb_open.setCurrentIndex(-1)
        self.cb_type.setCurrentIndex(-1)
        self.rs_production_year.set_left_thumb_value(1900)
        self.rs_production_year.set_right_thumb_value(2100)

        self.metaTextBrowser.clear()
        self.mdl_search_result.clear()
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

    def _simple_search(self, text: str):
        """launch simple search using suggest API

        :param text: text to search
        :type text: str
        """
        if len(text) > 2:
            self.mdl_search_result.simple_search_text(text)

    def _advanced_search(self):
        """launch advanced search using search API"""
        search_dict = {}
        if len(self.le_title.text()) > 0:
            search_dict["title"] = self.le_title.text()
        if len(self.le_layername.text()) > 0:
            search_dict["layer_name"] = self.le_layername.text()
        if self.cb_open.currentIndex() >= 0:
            search_dict["open"] = self.cb_open.currentText()
        if self.cb_type.currentIndex() >= 0:
            search_dict["type"] = self.cb_type.currentText()
        if len(self.le_theme.text()) > 0:
            search_dict["theme"] = self.le_theme.text()
        if len(self.le_producer.text()) > 0:
            search_dict["producer"] = self.le_producer.text()
        if len(self.le_keywords.text()) > 0:
            search_dict["keywords"] = self.le_keywords.text()
        # if self.sb_pymin.value() > 0:
        #     search_dict["production_year"] = self.le_title.text()
        # if self.sb_pymax.value() > 0:
        #     search_dict["production_year"] = self.le_title.text()
        if len(search_dict.keys()) > 0:
            self.mdl_search_result.advanced_search_text(search_dict)

    def _item_clicked(self, index: QModelIndex):
        """Display metadata when a result is selected

        :param index: selected index
        :type index: QModelIndex
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setEnabled(True)
        self.metaTextBrowser.clear()
        result = self.mdl_search_result.get_result(index)
        if result:
            self.metaTextBrowser.setText(json.dumps(result, indent=2))

    def _add_layer(self, index: QModelIndex):
        """Add selected layer to QGIS project

        :param index: selected index
        :type index: QModelIndex
        """
        result = self.mdl_search_result.get_result(index)
        layer = None
        if result:
            authid = None
            if result["open"] is False:
                auth_dlg = ChooseAuthenticationDialog()
                if auth_dlg.exec():
                    authid = auth_dlg.authent.configId()
                    print(authid)
                else:
                    return
            if result["type"] == "WMS":
                url = f"crs={result['srs'][0]}&format=image/png&layers={result['layer_name']}&styles&url={result['url'].split('?')[0]}"
                layer = QgsRasterLayer(url, result["title"], "wms")

            if result["type"] == "TMS":
                params = read_tms_layer_capabilities(result["url"])
                if params["format"] == "pbf":
                    url = (
                        "type=xyz&crs="
                        + result["srs"][0]
                        + f"&zmax={params['zmax']}"
                        + f"&zmin={params['zmin']}"
                        + "&url="
                        + result["url"]
                        + "/{z}/{x}/{y}.pbf"
                    )
                    layer = QgsVectorTileLayer(url, result["title"])
                elif params["format"] is not None:
                    url = (
                        "type=xyz&crs="
                        + result["srs"][0]
                        + "&url="
                        + result["url"]
                        + "/{z}/{x}/{y}."
                        + params["format"]
                    )
                    layer = QgsRasterLayer(url, result["title"], "wms")

            if result["type"] == "WMTS":
                params = read_wmts_layer_capabilities(
                    result["url"].split("?")[0], result["layer_name"]
                )
                if params:
                    url = f"crs={result['srs'][0]}&format={params['format']}&layers={result['layer_name']}&styles={params['style']}&tileMatrixSet={params['tileMatrixSet']}&url={result['url'].split('?')[0]}?SERVICE%3DWMTS%26version%3D1.0.0%26request%3DGetCapabilities"
                    layer = QgsRasterLayer(url, result["title"], "wms")

            if result["type"] == "WFS":
                url = f"{result['url'].split('?')[0]}?typename={result['layer_name']}&version=auto"
                layer = QgsVectorLayer(url, result["title"], "WFS")

        if layer is not None:
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
            else:
                self.log(
                    "Layer failed to load !",
                    log_level=2,
                    push=False,
                )

    def onAccept(self, button):
        """
        Lorsque l'utilisateur valide
        """
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.ButtonRole.ApplyRole:
            indexes = self.tbv_results.selectedIndexes()
            if len(indexes) > 0:
                self._add_layer(indexes[0])
            self.accept()
