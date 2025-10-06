import json
import logging
import os
import webbrowser
from typing import Optional

from qgis.core import (
    QgsMapBoxGlStyleConverter,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsVectorTileLayer,
)
from qgis.gui import QgsAbstractDataSourceWidget, QgsGui
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex, QUrl
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
)

from geoplateforme.constants import metadata_topic_categories
from geoplateforme.gui.metadata.wdg_tagbar import DictTagBarWidget
from geoplateforme.gui.provider.capabilities_reader import (
    read_tms_layer_capabilities,
    read_wmts_layer_capabilities,
)
from geoplateforme.gui.provider.choose_authentication_dialog import (
    ChooseAuthenticationDialog,
)
from geoplateforme.gui.provider.mdl_search_result import SearchResultModel
from geoplateforme.gui.provider.select_style_dialog import SelectStyleDialog
from geoplateforme.gui.provider.wdg_range_slider import QtRangeSlider
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger

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

        self.tb_thematics = DictTagBarWidget(metadata_topic_categories)
        self.layout_advanced_search.addWidget(self.tb_thematics, 6, 5, 1, 3)
        # Warning, thematics was hidden temporarly, waiting an upgrade from search API (see: https://github.com/Geoplateforme/plugin-qgis-geoplateforme/issues/209)
        self.lb_theme.hide()
        self.tb_thematics.hide()

        self.rs_production_year = QtRangeSlider(self, 1800, 2200, 1900, 2100)
        self.rs_production_year.left_thumb_value_changed.connect(
            lambda x: self.lb_py_min.setText(str(x))
        )
        self.rs_production_year.right_thumb_value_changed.connect(
            lambda x: self.lb_py_max.setText(str(x))
        )
        self.layout_advanced_search.addWidget(self.rs_production_year, 4, 6)

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
        self.tbv_results.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.tbv_results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_results.selectionModel().selectionChanged.connect(
            self._item_selection_changed
        )
        self.tbv_results.doubleClicked.connect(self._add_layer)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setText("Ajouter")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

        self._show_pagination(False)
        self._advanced_page = 1
        self.btn_next.clicked.connect(
            lambda: self._advanced_search(self._advanced_page + 1)
        )
        self.btn_previous.clicked.connect(
            lambda: self._advanced_search(self._advanced_page - 1)
        )
        self.tw_search.currentChanged.connect(self._swith_tab)

        self.le_search.textChanged.connect(self._simple_search)
        self.sb_max_results.valueChanged.connect(self._simple_search)
        self.btn_search.clicked.connect(self._advanced_search)
        self.btn_clear_search.clicked.connect(self._clear_search)
        self.buttonBox.clicked.connect(self.onAccept)

    def _clear_search(self):
        """clear search results"""
        self.le_search.clear()

        self.le_title.clear()
        self.le_layername.clear()
        self.tb_thematics.clear()
        self.le_producer.clear()
        self.le_keywords.clear()
        self.cb_open.setCurrentIndex(-1)
        self.cb_type.setCurrentIndex(-1)
        self.rs_production_year.set_left_thumb_value(1900)
        self.rs_production_year.set_right_thumb_value(2100)

        self.btn_next.setEnabled(False)
        self.btn_previous.setEnabled(False)

        self._clear_metadata()
        self.mdl_search_result.clear()
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setEnabled(False)

    def _swith_tab(self):
        """Switch search type (simple or advanced)"""
        self._clear_search()
        if self.tw_search.currentWidget().objectName() == "tab_simple_search":
            self._show_pagination(False)
        else:
            self._show_pagination(True)

    def _show_pagination(self, val: bool = True):
        """Show pagination buttons"""
        if val:
            self.btn_next.show()
            self.btn_previous.show()
        else:
            self.btn_next.hide()
            self.btn_previous.hide()

    def _simple_search(self):
        """launch simple search using suggest API

        :param text: text to search
        :type text: str
        """
        text = self.le_search.text()
        nb_results = self.sb_max_results.value()
        if len(text) > 2:
            self._clear_metadata()
            self.mdl_search_result.simple_search_text(text, nb_results)

    def _advanced_search(self, page: Optional[int]):
        """launch advanced search using search API"""
        if not page:
            page = 1
        self._advanced_page = page

        self._clear_metadata()

        search_dict = {}
        if len(self.le_title.text()) > 0:
            search_dict["title"] = self.le_title.text()
        if len(self.le_layername.text()) > 0:
            search_dict["layer_name"] = self.le_layername.text()
        if self.cb_open.currentIndex() >= 0:
            search_dict["open"] = self.cb_open.currentText()
        if self.cb_type.currentIndex() >= 0:
            search_dict["type"] = self.cb_type.currentText()
        if len(self.tb_thematics.tags) > 0:
            search_dict["theme"] = ", ".join(self.tb_thematics.tags)
        if len(self.le_producer.text()) > 0:
            search_dict["producers"] = self.le_producer.text()
        if len(self.le_keywords.text()) > 0:
            search_dict["keywords"] = self.le_keywords.text()
        if (
            self.rs_production_year.get_left_thumb_value() != 1900
            or self.rs_production_year.get_right_thumb_value() != 2100
        ):
            search_dict["production_years"] = {
                "min": self.rs_production_year.get_left_thumb_value(),
                "max": self.rs_production_year.get_right_thumb_value(),
            }
        if len(search_dict.keys()) > 0:
            nb_result = self.mdl_search_result.advanced_search_text(
                search_dict, self._advanced_page
            )
            if nb_result == 50:
                self.btn_next.setEnabled(True)
            else:
                self.btn_next.setEnabled(False)
            if self._advanced_page == 1:
                self.btn_previous.setEnabled(False)
            else:
                self.btn_previous.setEnabled(True)

    def _item_selection_changed(self) -> None:
        """Display metadata when a result is selected"""
        selected_indexes = self.tbv_results.selectionModel().selectedIndexes()
        if len(selected_indexes):
            index = selected_indexes[0]
            self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setEnabled(
                True
            )
            self._clear_metadata()
            result = self.mdl_search_result.get_result(index)
            if result:
                self._display_metadata(result)

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
                metadata_url = None
                if "metadata_urls" in result and len(result["metadata_urls"]) > 0:
                    for url in result["metadata_urls"]:
                        if "cartes.gouv.fr" in url:
                            metadata_url = url
                if metadata_url is not None:
                    auth_dlg = ChooseAuthenticationDialog(metadata_url)
                else:
                    auth_dlg = ChooseAuthenticationDialog()
                if auth_dlg.exec():
                    authid = auth_dlg.authent.configId()
                else:
                    return
            if result["type"] == "WMS":
                url = f"crs={result['srs'][0]}&format=image/png&layers={result['layer_name']}&styles&url={result['url'].split('?')[0]}"
                if authid is not None:
                    url = f"authcfg={authid}&" + url
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
                    if authid is not None:
                        url = f"authcfg={authid}&" + url
                    layer = QgsVectorTileLayer(url, result["title"])
                    style = None
                    if len(params["styles"]) > 0:
                        style_dlg = SelectStyleDialog(params["styles"])
                        if style_dlg.exec():
                            style = style_dlg.style_combo.currentText()
                    if style is not None and len(style) > 0:
                        network_manager = NetworkRequestsManager()
                        reply = network_manager.get_url(url=QUrl(style))
                        style_json = json.loads(reply.data())
                        converter = QgsMapBoxGlStyleConverter()
                        status = converter.convert(style_json)
                        if status == QgsMapBoxGlStyleConverter.Result.Success:
                            layer.setRenderer(converter.renderer().clone())
                            layer.setLabeling(converter.labeling().clone())
                elif params["format"] is not None:
                    url = (
                        "type=xyz&crs="
                        + result["srs"][0]
                        + "&url="
                        + result["url"]
                        + "/{z}/{x}/{y}."
                        + params["format"]
                    )
                    if authid is not None:
                        url = f"authcfg={authid}&" + url
                    layer = QgsRasterLayer(url, result["title"], "wms")

            if result["type"] == "WMTS":
                params = read_wmts_layer_capabilities(
                    result["url"].split("?")[0], result["layer_name"], authid
                )
                if params:
                    url = f"crs={result['srs'][0]}&format={params['format']}&layers={result['layer_name']}&styles={params['style']}&tileMatrixSet={params['tileMatrixSet']}&url={result['url'].split('?')[0]}?SERVICE%3DWMTS%26version%3D1.0.0%26request%3DGetCapabilities"
                    if authid is not None:
                        url = f"authcfg={authid}&" + url
                    layer = QgsRasterLayer(url, result["title"], "wms")

            if result["type"] == "WFS":
                url = f"{result['url'].split('?')[0]}?typename={result['layer_name']}&version=auto"
                if authid is not None:
                    url += f"&authcfg={authid}"
                layer = QgsVectorLayer(url, result["title"], "WFS")
                if layer.isValid():
                    dlg_sub_wfs = (
                        QgsGui.subsetStringEditorProviderRegistry().createDialog(layer)
                    )
                    if not dlg_sub_wfs.exec():
                        layer = None

        if layer is not None:
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
            else:
                self.log(
                    "Layer failed to load !",
                    log_level=2,
                    push=False,
                )

    def _display_metadata(self, metadata: dict):
        """Display metadata informations

        :param metadata: metadata informations
        :type metadata: dict
        """
        display_items = {
            "title": self.tr("title"),
            "layer_name": self.tr("layer_name"),
            "description": self.tr("description"),
            "type": self.tr("type"),
            "open": self.tr("open"),
            "publication_date": self.tr("publication_date"),
            "srs": self.tr("srs"),
            "keywords": self.tr("keywords"),
        }
        item_number = 0

        metadata_url = None
        if "metadata_urls" in metadata and len(metadata["metadata_urls"]) > 0:
            for url in metadata["metadata_urls"]:
                if "cartes.gouv.fr" in url:
                    metadata_url = url
        if metadata_url is not None:
            link = QPushButton()
            link.setText(self.tr("Open in cartes.gouv.fr"))
            link.clicked.connect(lambda: webbrowser.open(metadata_url))
            self.metadataLayout.addWidget(link, item_number, 0, 1, 2)
            item_number += 1

        for item in display_items:
            if item in metadata:
                label = QLabel()
                label.setText(f"<b>{display_items[item]} :</b>")
                if item == "description":
                    text = QTextEdit()
                else:
                    text = QLineEdit()
                text.setReadOnly(True)
                if isinstance(metadata[item], list):
                    text.setText(str(",".join(metadata[item])))
                else:
                    text.setText(str(metadata[item]))
                self.metadataLayout.addWidget(label, item_number, 0)
                self.metadataLayout.addWidget(text, item_number, 1)
                item_number += 1

    def _clear_metadata(self):
        """clear metadata informations"""
        while self.metadataLayout.count():
            item = self.metadataLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self.clearLayout(item.layout())

    def onAccept(self, button):
        """
        Lorsque l'utilisateur valide
        """
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.ButtonRole.ApplyRole:
            indexes = self.tbv_results.selectedIndexes()
            if len(indexes) > 0:
                self._add_layer(indexes[0])
            self.accept()
