import os
from typing import Optional

from qgis.core import (
    QgsApplication,
    QgsMapLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QToolBar, QToolButton, QWidget

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.configuration import ConfigurationType
from geoplateforme.api.offerings import Offering, OfferingStatus
from geoplateforme.gui.create_raster_tiles_from_wms_vector.wzd_raster_tiles_from_wms_vector import (
    TileRasterCreationWizard,
)
from geoplateforme.gui.provider.capabilities_reader import read_wmts_layer_capabilities
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.delete_offering import DeleteOfferingAlgorithm
from geoplateforme.toolbelt import PlgLogger


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

        # Add toolbar for stored data actions
        self.edit_toolbar = QToolBar(self)
        self.layout().setMenuBar(self.edit_toolbar)

        self.gpb_permissions.setVisible(False)

        self.tile_raster_generation_wizard = None

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

        # Only published offering have actions
        if status == OfferingStatus.PUBLISHED:
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
            self.edit_toolbar.addWidget(button)

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
            self.edit_toolbar.addWidget(button)

            self.gpb_permissions.setVisible(not offering.open)
            if not offering.open:
                self.wdg_permissions.refresh(offering.datastore_id, offering._id)

            # Styles
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
                self.edit_toolbar.addWidget(button)

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
            alg = QgsApplication.processingRegistry().algorithmById(algo_str)
            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()
            _, success = alg.run(parameters=params, context=context, feedback=feedback)
            if success:
                self.offering_deleted.emit(self._offering._id)
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Dépublication service"),
                    self.tr("Le service n'a pas pu être dépublié :\n {}").format(
                        feedback.textLog()
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

    def _offering_map_layer(self) -> Optional[QgsMapLayer]:
        urls = self._offering.urls
        if self._offering.type == ConfigurationType.WFS:
            for val in urls:
                if val["type"] == "WFS":
                    url = val["url"].replace("typeNames", "typename")
                    return QgsVectorLayer(url, self._offering.layer_name, "WFS")
        if (
            self._offering.type == ConfigurationType.WMS_RASTER
            or self._offering.type == ConfigurationType.WMS_VECTOR
        ):
            for val in urls:
                if val["type"] == "WMS":
                    # TODO : comment définir le CRS
                    url = f"crs=EPSG:4326&format=image/png&layers={self._offering.layer_name}&styles&url={val['url'].split('?')[0]}?GetCapabilities"
                    return QgsRasterLayer(url, self._offering.layer_name, "wms")
        if self._offering.type == ConfigurationType.WMTS_TMS:
            for val in urls:
                if val["type"] == "WMTS":
                    params = read_wmts_layer_capabilities(
                        val["url"].split("?")[0],
                        self._offering.configuration.name,
                    )
                    if params:
                        # TODO : define url
                        url = "invalid"
                        # url = f"format={params['format']}&layers={self._offering.layer_name}&styles={params['style']}&tileMatrixSet={params['tileMatrixSet']}&url={result['url'].split('?')[0]}?SERVICE%3DWMTS%26version%3D1.0.0%26request%3DGetCapabilities"
                        return QgsRasterLayer(url, self._offering.layer_name, "wms")
        if self._offering.type == ConfigurationType.VECTOR_TMS:
            return None

        return None

    def load_offering(self) -> None:
        layer = self._offering_map_layer()
        if layer:
            QgsProject.instance().addMapLayer(layer)
