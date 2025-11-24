import json
import os
import re
import webbrowser
from tempfile import NamedTemporaryFile
from typing import Optional

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapBoxGlStyleConverter,
    QgsMapLayer,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsVectorTileLayer,
)
from qgis.gui import QgsGui
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QSize, Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAction,
    QLayout,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QWidget,
)
from qgis.utils import iface

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.configuration import ConfigurationType
from geoplateforme.api.offerings import Offering, OfferingStatus
from geoplateforme.constants import cartes_gouv_template_url
from geoplateforme.gui.create_raster_tiles_from_wms_vector.wzd_raster_tiles_from_wms_vector import (
    TileRasterCreationWizard,
)
from geoplateforme.gui.dashboard.dlg_select_layer_and_style import (
    SelectLayerAndStyleDialog,
)
from geoplateforme.gui.provider.capabilities_reader import read_tms_layer_capabilities
from geoplateforme.gui.provider.choose_authentication_dialog import (
    ChooseAuthenticationDialog,
)
from geoplateforme.gui.provider.select_style_dialog import SelectStyleDialog
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.delete_offering import DeleteOfferingAlgorithm
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger
from geoplateforme.toolbelt.dlg_processing_run import ProcessingRunDialog
from geoplateforme.toolbelt.preferences import PlgOptionsManager


class ServiceDetailsWidget(QWidget):
    select_stored_data = pyqtSignal(str)
    offering_deleted = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        """
        QWidget to display report for an upload

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_service_details.ui"),
            self,
        )

        self.setWindowTitle(self.tr("Details"))

        self._offering = None
        self._dataset_name = None

        self.gpb_permissions.setVisible(False)

        self.btn_view_style.clicked.connect(self._open_view_style_url)
        self.btn_add_style.clicked.connect(self._open_create_style_url)

        self.tile_raster_generation_wizard = None

    def _open_view_style_url(self) -> None:
        """Open view style URL on webbrowser"""
        self._open_style_url(
            PlgOptionsManager.get_plg_settings().url_geoplateforme.rstrip("/")
            + cartes_gouv_template_url["view_style"]
        )

    def _open_create_style_url(self) -> None:
        """Open create style URL on webbrowser"""
        self._open_style_url(
            PlgOptionsManager.get_plg_settings().url_geoplateforme.rstrip("/")
            + cartes_gouv_template_url["create_style"]
        )

    def _open_style_url(self, template_url: str) -> None:
        """Open document URL on webbrowser"""
        datastore_id = self._offering.datastore_id
        dataset_name = self._dataset_name
        offering_id = self._offering._id
        url = template_url.replace("{datastore_id}", datastore_id)
        url = url.replace("{dataset_name}", dataset_name)
        url = url.replace("{offering_id}", offering_id)
        webbrowser.open(url)

    def set_offering(self, offering: Offering, dataset_name: str) -> None:
        """
        Define displayed offering

        Args:
            offering: Offering
        """
        self._offering = offering
        self._dataset_name = dataset_name
        self._set_offering_details(offering)

    def _load_icon(self) -> QIcon:
        if self._offering.type == ConfigurationType.WFS:
            return QIcon(":images/themes/default/mActionAddWfsLayer.svg")
        if (
            self._offering.type == ConfigurationType.WMTS_TMS
            or self._offering.type == ConfigurationType.WMS_RASTER
            or self._offering.type == ConfigurationType.WMS_VECTOR
        ):
            return QIcon(":images/themes/default/mActionAddWmsLayer.svg")

        if self._offering.type == ConfigurationType.VECTOR_TMS:
            return QIcon(":images/themes/default/mActionAddVectorTileLayer.svg")

    def clear_layout(self, layout: QLayout) -> None:
        """Remove all widgets from a layout and delete them.

        :param layout: layout to clear
        :type layout: QLayout
        """
        while layout.count():
            item = layout.takeAt(0)  # Take item from position 0
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # Detach from layout
                widget.deleteLater()  # Schedule for deletion
            else:
                # If it's a nested layout, clear it recursively
                sub_layout = item.layout()
                if sub_layout is not None:
                    self.clear_layout(sub_layout)

    def _set_offering_details(self, offering: Offering) -> None:
        """
        Define offering details

        Args:
            offering: (Offering)
        """
        status = offering.status
        self.lbl_status_icon.setText("")
        self.lbl_status_icon.setPixmap(self._get_status_icon(status))
        self.lbl_status.setText(self._get_status_text(offering))

        self.lne_name.setText(offering.layer_name)
        self.lne_id.setText(offering._id)

        self.gpb_styles.setVisible(False)

        # Remove all available action
        self.clear_layout(self.action_layout)

        # Add delete action for PUBLISHED or UNSTABLE offering
        if status == OfferingStatus.PUBLISHED or status == OfferingStatus.UNSTABLE:
            # Data delete
            delete_action = QAction(
                QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Supprimer.svg")),
                self.tr("Dépublication"),
                self,
            )
            delete_action.triggered.connect(self.delete_offering)
            button = QToolButton(self)
            button.setDefaultAction(delete_action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.action_layout.addWidget(button)

        # Add load action for published offering
        if status == OfferingStatus.PUBLISHED:
            # Load service
            load_action = QAction(
                self._load_icon(),
                self.tr("Charger"),
                self,
            )
            load_action.triggered.connect(self.load_offering)
            button = QToolButton(self)
            button.setDefaultAction(load_action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.action_layout.addWidget(button)

            self.gpb_permissions.setVisible(not offering.open)
            if not offering.open:
                self.wdg_permissions.refresh(offering.datastore_id, offering._id)

            style_enable = offering.type in [
                ConfigurationType.WFS,
                ConfigurationType.VECTOR_TMS,
            ]

            if offering.type == ConfigurationType.WMTS_TMS:
                urls = offering.urls
                for val in urls:
                    if val["type"] == "TMS":
                        params = read_tms_layer_capabilities(val["url"])
                        if params and params["format"] == "pbf":
                            style_enable = True
                            break

            # Styles
            if style_enable:
                self.gpb_styles.setVisible(True)
                self.wdg_styles.set_configuration(offering.configuration)

            # WMS_VECTOR :
            # - raster tile generation
            if offering.type == ConfigurationType.WMS_VECTOR:
                # Raster tile generation
                generate_tile_action = QAction(
                    QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Tuile@1x.png")),
                    self.tr("Génération tuile"),
                    self,
                )
                generate_tile_action.triggered.connect(
                    self._show_tile_raster_generation_wizard
                )
                button = QToolButton(self)
                button.setDefaultAction(generate_tile_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                self.action_layout.addWidget(button)

        # Add spacer to have button align left
        self.action_layout.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

    def _show_tile_raster_generation_wizard(self) -> None:
        """Show tile generation wizard for current offerring"""
        self._generate_tile_raster_wizard(self._offering, self._dataset_name)

    def _generate_tile_raster_wizard(
        self, offering: Offering, dataset_name: str
    ) -> None:
        """
        Show tile raster generation wizard for a offerring

        Args:
            offering: (Offering) offerring to generate tile
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.tile_raster_generation_wizard = TileRasterCreationWizard(
            datastore_id=offering.datastore_id,
            dataset_name=dataset_name,
            offering_id=offering._id,
            parent=self,
        )
        QGuiApplication.restoreOverrideCursor()
        self.tile_raster_generation_wizard.finished.connect(
            self._del_tile_raster_generation_wizard
        )
        self.tile_raster_generation_wizard.show()

    def _del_tile_raster_generation_wizard(self) -> None:
        """
        Delete wms vector publish wizard

        """
        if self.tile_raster_generation_wizard is not None:
            stored_data_id = (
                self.tile_raster_generation_wizard.get_created_stored_data_id()
            )
            if stored_data_id:
                self.select_stored_data.emit(stored_data_id)
            self.tile_raster_generation_wizard.deleteLater()
            self.tile_raster_generation_wizard = None

    def delete_offering(self) -> None:
        """Delete current offering"""
        reply = QMessageBox.question(
            self,
            self.tr("Dépublication"),
            self.tr("Êtes-vous sûr de vouloir dépublier le service ?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            params = {
                DeleteOfferingAlgorithm.DATASTORE: self._offering.datastore_id,
                DeleteOfferingAlgorithm.OFFERING: self._offering._id,
            }
            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteOfferingAlgorithm().name()}"
            )
            run_dialog = ProcessingRunDialog(
                alg_name=algo_str,
                params=params,
                title=self.tr("Unpublish service {}").format(self._offering.layer_name),
                parent=self,
            )
            run_dialog.exec()
            success, _ = run_dialog.processing_results()
            if success:
                self.offering_deleted.emit(self._offering._id)
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Dépublication service"),
                    self.tr("Le service n'a pas pu être dépublié :\n {}").format(
                        run_dialog.get_feedback().textLog()
                    ),
                )

    def _get_status_text(self, offering: Offering) -> str:
        """
        Define status text from an offering

        Args:
            offering: (Offering) offering

        Returns: status text

        """
        status = offering.status
        if status == OfferingStatus.PUBLISHING:
            result = self.tr("Publication en cours.")
        elif status == OfferingStatus.MODIFYING:
            result = self.tr("Publication en cours de modification.")
        elif status == OfferingStatus.PUBLISHED:
            result = self.tr("Publication réussie.")
        elif status == OfferingStatus.UNPUBLISHING:
            result = self.tr("Dépublication en cours.")
            result += self.tr(
                " You will find above technical information about processing executed and encountered "
                "problem."
            )
        elif status == OfferingStatus.UNSTABLE:
            result = self.tr("Publication instable.")
        else:
            result = ""
        return result

    @staticmethod
    def _get_status_icon(status: OfferingStatus) -> QPixmap:
        """
        Get status icon

        Args:
            status: UploadStatus

        Returns: QPixmap

        """
        if status == OfferingStatus.PUBLISHING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == OfferingStatus.MODIFYING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == OfferingStatus.UNSTABLE:
            result = QIcon(QgsApplication.iconPath("mIconWarning.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == OfferingStatus.MODIFYING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        else:
            # PUBLISHED
            result = QIcon(QgsApplication.iconPath("mIconSuccess.svg")).pixmap(
                QSize(16, 16)
            )

        return result

    def _offering_map_layer(self, authid: str | None = None) -> Optional[QgsMapLayer]:
        urls = self._offering.urls
        if self._offering.type == ConfigurationType.WFS:
            urls = [val["url"] for val in self._offering.urls if val["type"] == "WFS"]
            if len(urls) > 0:
                layers = []
                styles = []
                for val in urls:
                    match = re.findall(r"typeNames=(.*)", val)
                    if len(match) == 1:
                        layers.append({"name": match[0].split("&")[0], "url": val})
                extra = self._offering.configuration.extra
                if extra is not None:
                    config_style = extra.get("styles", None)
                    if config_style is not None:
                        for style in config_style:
                            styles.append(style)
                choose_dlg = SelectLayerAndStyleDialog(layers, styles)
                if choose_dlg.exec():
                    layer_name = choose_dlg.layer_combo.currentText()
                    style_name = choose_dlg.style_combo.currentText()
                    # get layer and style dict from selection
                    layer = [lay for lay in layers if lay["name"] == layer_name][0]
                    style = None
                    style_url = None
                    if style_name is not None and len(style_name) > 0:
                        style = [st for st in styles if st["name"] == style_name][0]
                        style_layer = [
                            layst
                            for layst in style["layers"]
                            if layst["name"] == layer["name"]
                        ]
                        if len(style_layer) == 1:
                            style_url = style_layer[0]["url"]
                    # load layer
                    layer_name_parts = layer["name"].split(":")
                    if len(layer_name_parts) == 2 and (
                        not layer_name_parts[1][0] == "_"
                        and not layer_name_parts[1][0].isalpha()
                    ):
                        QMessageBox.warning(
                            self,
                            "Incompatible layer",
                            f"""
                            The layer {layer["name"]} is imcompatible with QGIS.
                            Layername must start with a letter or underscore.
                            """,
                        )
                        return None

                    url = layer["url"].replace("typeNames", "typename")
                    if authid is not None:
                        url += f"&authcfg={authid}"
                    wfs_layer = QgsVectorLayer(url, layer["name"], "WFS")
                    if style_url is not None:
                        network_manager = NetworkRequestsManager()
                        temp_file_name = NamedTemporaryFile(suffix=".xml").name
                        network_manager.download_file_to(
                            remote_url=QUrl(style_url),
                            local_path=temp_file_name,
                        )
                        wfs_layer.loadSldStyle(temp_file_name)
                    if wfs_layer.isValid():
                        dlg_sub_wfs = (
                            QgsGui.subsetStringEditorProviderRegistry().createDialog(
                                wfs_layer
                            )
                        )
                        if not dlg_sub_wfs.exec():
                            wfs_layer = None
                    return wfs_layer
        if (
            self._offering.type == ConfigurationType.WMS_RASTER
            or self._offering.type == ConfigurationType.WMS_VECTOR
        ):
            for val in urls:
                if val["type"] == "WMS":
                    # Le CRS est défini a 3857 par defaut
                    url = f"crs=EPSG:3857&format=image/png&layers={self._offering.layer_name}&styles&url={val['url'].split('?')[0]}"
                    if authid is not None:
                        url = f"authcfg={authid}&" + url
                    return QgsRasterLayer(url, self._offering.layer_name, "wms")
        if self._offering.type == ConfigurationType.WMTS_TMS:
            for val in urls:
                if val["type"] == "TMS":
                    params = read_tms_layer_capabilities(val["url"])
                    if params["format"] == "pbf":
                        url = (
                            "type=xyz&crs="
                            + params["srs"]
                            + f"&zmax={params['zmax']}"
                            + f"&zmin={params['zmin']}"
                            + "&url="
                            + val["url"]
                            + "/{z}/{x}/{y}.pbf"
                        )
                        if authid is not None:
                            url = f"authcfg={authid}&" + url
                        layer = QgsVectorTileLayer(url, self._offering.layer_name)
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
                        return layer
                    elif params["format"] is not None:
                        url = (
                            "type=xyz&crs="
                            + params["srs"]
                            + "&url="
                            + val["url"]
                            + "/{z}/{x}/{y}."
                            + params["format"]
                        )
                        if authid is not None:
                            url = f"authcfg={authid}&" + url
                        return QgsRasterLayer(url, self._offering.layer_name, "wms")

        if self._offering.type == ConfigurationType.VECTOR_TMS:
            return None

        return None

    def load_offering(self) -> None:
        authid = None
        if self._offering.open is False:
            auth_dlg = ChooseAuthenticationDialog()
            if auth_dlg.exec():
                authid = auth_dlg.authent.configId()
            else:
                return
        layer = self._offering_map_layer(authid)
        if layer is not None and layer.isValid():
            QgsProject.instance().addMapLayer(layer)
        else:
            iface.messageBar().pushMessage(
                "Error", self.tr("Layer failed to load !"), level=Qgis.Critical
            )
