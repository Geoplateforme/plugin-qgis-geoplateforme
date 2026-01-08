import os

from qgis.core import QgsApplication, QgsProject
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QAction,
    QDialog,
    QHeaderView,
    QLayout,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QWidget,
)

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.custom_exceptions import (
    ReadStoredDataException,
    UnavailableExecutionException,
    UnavailableUploadException,
)
from geoplateforme.api.processing import ProcessingRequestManager
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataRequestManager,
    StoredDataStatus,
    StoredDataType,
)
from geoplateforme.api.upload import UploadRequestManager
from geoplateforme.gui.dlg_processing_run import ProcessingRunDialog
from geoplateforme.gui.mdl_table_relation import TableRelationTreeModel
from geoplateforme.gui.publication_creation.wzd_publication_creation import (
    PublicationFormCreation,
)
from geoplateforme.gui.report.mdl_stored_data_details import StoredDataDetailsModel
from geoplateforme.gui.report.wdg_execution_log import ExecutionLogWidget
from geoplateforme.gui.report.wdg_upload_log import UploadLogWidget
from geoplateforme.gui.tile_creation.wzd_tile_creation import TileCreationWizard
from geoplateforme.gui.wfs_publication.wzd_publication_creation import (
    WFSPublicationWizard,
)
from geoplateforme.gui.wms_raster_publication.wzd_publication_creation import (
    WMSRasterPublicationWizard,
)
from geoplateforme.gui.wms_vector_publication.wzd_publication_creation import (
    WMSVectorPublicationWizard,
)
from geoplateforme.gui.wmts_publication.wzd_publication_creation import (
    WMTSPublicationWizard,
)
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.delete_stored_data import DeleteStoredDataAlgorithm
from geoplateforme.toolbelt import PlgLogger


class StoredDataDetailsDialog(QDialog):
    select_stored_data = pyqtSignal(str)
    select_offering = pyqtSignal(str)
    stored_data_deleted = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        """
        QDialog to display report for a stored data

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "dlg_stored_data_details.ui"),
            self,
        )

        self.setWindowTitle(self.tr("Details"))

        self._stored_data = None

        self.mdl_stored_data_details = StoredDataDetailsModel(self)
        self.tbv_details.setModel(self.mdl_stored_data_details)
        self.tbv_details.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tbv_details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.mdl_table_relation = TableRelationTreeModel(self)
        self.mdl_table_relation.check_state_enabled = False
        self.trv_table_relation.setModel(self.mdl_table_relation)
        self.trv_table_relation.setSortingEnabled(True)

        self.trv_table_relation.header().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.trv_table_relation.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.btn_add_extent_layer.pressed.connect(self._add_extent_layer)
        self.btn_load_report.pressed.connect(self._load_generation_report)

        self.tile_generation_wizard = None
        self.wms_vector_publish_wizard = None
        self.wfs_publish_wizard = None
        self.tms_publish_wizard = None
        self.wms_raster_publish_wizard = None
        self.wmts_publish_wizard = None

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

    def set_stored_data(self, stored_data: StoredData) -> None:
        """
        Define displayed stored data

        Args:
            stored_data: StoredData
        """
        self._stored_data = stored_data
        self._set_stored_data_details(stored_data)

        # Remove all available action
        self.clear_layout(self.action_layout)

        status = stored_data.status

        # Add delete action for GENERATED, CREATED or UNSTABLE stored data
        if (
            status == StoredDataStatus.GENERATED
            or status == StoredDataStatus.CREATED
            or status == StoredDataStatus.UNSTABLE
        ):
            # Data delete
            delete_action = QAction(
                QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Supprimer.svg")),
                self.tr("Suppression"),
                self,
            )
            delete_action.triggered.connect(self.delete_stored_data)
            button = QToolButton(self)
            button.setDefaultAction(delete_action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.action_layout.addWidget(button)

        # Only generated stored data have publication and generation actions
        if status == StoredDataStatus.GENERATED:
            # Vector DB :
            # - tile generation
            # - WFS publication
            if stored_data.type == StoredDataType.VECTORDB:
                # Tile generation
                generate_tile_action = QAction(
                    QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Tuile@1x.png")),
                    self.tr("Génération tuile"),
                    self,
                )
                generate_tile_action.triggered.connect(
                    self._show_tile_generation_wizard
                )
                button = QToolButton(self)
                button.setDefaultAction(generate_tile_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
                self.action_layout.addWidget(button)

                # WFS publication
                publish_tile_action = QAction(
                    QIcon(
                        str(
                            DIR_PLUGIN_ROOT
                            / "resources"
                            / "images"
                            / "icons"
                            / "Publie@2x.png"
                        )
                    ),
                    self.tr("Publication WFS"),
                    self,
                )
                button = QToolButton(self)
                button.setDefaultAction(publish_tile_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

                publish_tile_action.triggered.connect(self._show_wfs_publish_wizard)
                self.action_layout.addWidget(button)

                wms_vector_publish_action = QAction(
                    QIcon(
                        str(
                            DIR_PLUGIN_ROOT
                            / "resources"
                            / "images"
                            / "icons"
                            / "Publie@2x.png"
                        )
                    ),
                    self.tr("Publication WMS-Vecteur"),
                    self,
                )
                button = QToolButton(self)
                button.setDefaultAction(wms_vector_publish_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

                wms_vector_publish_action.triggered.connect(
                    self._show_wms_vector_publish_wizard
                )
                self.action_layout.addWidget(button)

            elif stored_data.type == StoredDataType.PYRAMIDVECTOR:
                publish_tile_action = QAction(
                    QIcon(
                        str(
                            DIR_PLUGIN_ROOT
                            / "resources"
                            / "images"
                            / "icons"
                            / "Publie@2x.png"
                        )
                    ),
                    self.tr("Publication WMS-TMS"),
                    self,
                )
                button = QToolButton(self)
                button.setDefaultAction(publish_tile_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

                publish_tile_action.triggered.connect(self._show_tile_publish_wizard)
                self.action_layout.addWidget(button)
            elif stored_data.type == StoredDataType.PYRAMIDRASTER:
                publish_tile_action = QAction(
                    QIcon(
                        str(
                            DIR_PLUGIN_ROOT
                            / "resources"
                            / "images"
                            / "icons"
                            / "Publie@2x.png"
                        )
                    ),
                    self.tr("Publication WMS-Raster"),
                    self,
                )
                button = QToolButton(self)
                button.setDefaultAction(publish_tile_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

                publish_tile_action.triggered.connect(
                    self._show_raster_tile_publish_wizard
                )
                self.action_layout.addWidget(button)

                # WMTS-TMS publication
                publish_wmts_action = QAction(
                    QIcon(
                        str(
                            DIR_PLUGIN_ROOT
                            / "resources"
                            / "images"
                            / "icons"
                            / "Publie@2x.png"
                        )
                    ),
                    self.tr("Publication WMTS-TMS"),
                    self,
                )
                button = QToolButton(self)
                button.setDefaultAction(publish_wmts_action)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

                publish_wmts_action.triggered.connect(self._show_wmts_publish_wizard)
                self.action_layout.addWidget(button)

        # Add spacer to have button align left
        self.action_layout.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

    def delete_stored_data(self) -> None:
        """Delete current stored data"""
        reply = QMessageBox.question(
            self,
            self.tr("Suppression donnée stockée"),
            self.tr(
                "Êtes-vous sûr de vouloir supprimer la donnée stockée ?\nLes services et styles associés seront dépubliés."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            params = {
                DeleteStoredDataAlgorithm.DATASTORE: self._stored_data.datastore_id,
                DeleteStoredDataAlgorithm.STORED_DATA: self._stored_data._id,
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteStoredDataAlgorithm().name()}"
            )
            run_dialog = ProcessingRunDialog(
                alg_name=algo_str,
                params=params,
                title=self.tr("Delete stored data {}").format(self._stored_data.name),
                parent=self,
            )
            run_dialog.exec()
            success, _ = run_dialog.processing_results()
            if success:
                self.stored_data_deleted.emit(self._stored_data._id)
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Suppression donnée stockée"),
                    self.tr("La donnée stockée n'a pas pu être supprimée:\n {}").format(
                        run_dialog.get_feedback().textLog()
                    ),
                )

    def _show_raster_tile_publish_wizard(self) -> None:
        """Show wms vector publication wizard for current stored data"""
        self._raster_tile_publish_wizard(self._stored_data)

    def _raster_tile_publish_wizard(self, stored_data: StoredData) -> None:
        """
        Show wms vector publication wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to generate tile
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.wms_raster_publish_wizard = WMSRasterPublicationWizard(
            self,
            stored_data.datastore_id,
            stored_data.tags["datasheet_name"],
            stored_data._id,
        )
        QGuiApplication.restoreOverrideCursor()
        self.wms_raster_publish_wizard.finished.connect(
            self._del_wms_raster_publish_wizard
        )
        self.wms_raster_publish_wizard.show()

    def _del_wms_raster_publish_wizard(self) -> None:
        """
        Delete wms raster publish wizard

        """
        if self.wms_raster_publish_wizard is not None:
            offering_id = self.wms_raster_publish_wizard.get_offering_id()
            if offering_id:
                self.select_offering.emit(offering_id)
            self.wms_raster_publish_wizard.deleteLater()
            self.wms_raster_publish_wizard = None

    def _show_wmts_publish_wizard(self) -> None:
        """Show wmts publication wizard for current stored data"""
        self._wmts_publish_wizard(self._stored_data)

    def _wmts_publish_wizard(self, stored_data: StoredData) -> None:
        """
        Show wmts publication wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to generate tile
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.wmts_publish_wizard = WMTSPublicationWizard(
            self,
            stored_data.datastore_id,
            stored_data.tags["datasheet_name"],
            stored_data._id,
        )
        QGuiApplication.restoreOverrideCursor()
        self.wmts_publish_wizard.finished.connect(self._del_wmts_publish_wizard)
        self.wmts_publish_wizard.show()

    def _del_wmts_publish_wizard(self) -> None:
        """
        Delete wmts publish wizard

        """
        if self.wmts_publish_wizard is not None:
            offering_id = self.wmts_publish_wizard.get_offering_id()
            if offering_id:
                self.select_offering.emit(offering_id)
            self.wmts_publish_wizard.deleteLater()
            self.wmts_publish_wizard = None

    def _show_wms_vector_publish_wizard(self) -> None:
        """Show wms vector publication wizard for current stored data"""
        self._wms_vector_publish_wizard(self._stored_data)

    def _wms_vector_publish_wizard(self, stored_data: StoredData) -> None:
        """
        Show wms vector publication wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to generate tile
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.wms_vector_publish_wizard = WMSVectorPublicationWizard(
            stored_data,
            self,
            stored_data.datastore_id,
            stored_data.tags["datasheet_name"],
        )
        QGuiApplication.restoreOverrideCursor()
        self.wms_vector_publish_wizard.finished.connect(
            self._del_wms_vector_publish_wizard
        )
        self.wms_vector_publish_wizard.show()

    def _del_wms_vector_publish_wizard(self) -> None:
        """
        Delete wms vector publish wizard

        """
        if self.wms_vector_publish_wizard is not None:
            offering_id = self.wms_vector_publish_wizard.get_offering_id()
            if offering_id:
                self.select_offering.emit(offering_id)
            self.wms_vector_publish_wizard.deleteLater()
            self.wms_vector_publish_wizard = None

    def _show_tile_generation_wizard(self) -> None:
        """Show tile generation wizard for current stored data"""
        self._generate_tile_wizard(self._stored_data)

    def _generate_tile_wizard(self, stored_data: StoredData) -> None:
        """
        Show tile generation wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to generate tile
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.tile_generation_wizard = TileCreationWizard(
            stored_data.datastore_id,
            stored_data.tags["datasheet_name"],
            stored_data._id,
            self,
        )
        QGuiApplication.restoreOverrideCursor()
        self.tile_generation_wizard.finished.connect(self._del_tile_generation_wizard)
        self.tile_generation_wizard.show()

    def _del_tile_generation_wizard(self) -> None:
        """
        Delete tile generation wizard

        """
        if self.tile_generation_wizard is not None:
            created_stored_data_id = (
                self.tile_generation_wizard.get_created_stored_data_id()
            )
            if created_stored_data_id:
                self.select_stored_data.emit(created_stored_data_id)
            self.tile_generation_wizard.deleteLater()
            self.tile_generation_wizard = None

    def _show_tile_publish_wizard(self) -> None:
        """Show tile generation wizard for current stored data"""
        self._tile_publish_wizard(self._stored_data)

    def _tile_publish_wizard(self, stored_data: StoredData) -> None:
        """
        Show publish wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to publish
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.tms_publish_wizard = PublicationFormCreation(
            self,
            stored_data.datastore_id,
            stored_data.tags["datasheet_name"],
            stored_data._id,
        )
        QGuiApplication.restoreOverrideCursor()
        self.tms_publish_wizard.finished.connect(self._del_tms_publish_wizard)
        self.tms_publish_wizard.show()

    def _del_tms_publish_wizard(self) -> None:
        """
        Delete tm publish wizard

        """
        if self.tms_publish_wizard is not None:
            offering_id = self.tms_publish_wizard.get_offering_id()
            if offering_id:
                self.select_offering.emit(offering_id)
            self.tms_publish_wizard.deleteLater()
            self.tms_publish_wizard = None

    def _show_wfs_publish_wizard(self) -> None:
        """Show WFS publication wizard for current stored data"""
        self._wfs_publish_wizard(self._stored_data)

    def _wfs_publish_wizard(self, stored_data: StoredData) -> None:
        """Show WFS publication wizard for a stored data

        :param stored_data: stored data
        :type stored_data: StoredData
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.wfs_publish_wizard = WFSPublicationWizard(
            self,
            stored_data.datastore_id,
            stored_data.tags["datasheet_name"],
            stored_data,
        )
        QGuiApplication.restoreOverrideCursor()
        self.wfs_publish_wizard.finished.connect(self._del_wfs_publish_wizard)
        self.wfs_publish_wizard.show()

    def _del_wfs_publish_wizard(self) -> None:
        """
        Delete wfs publish wizard

        """
        if self.wfs_publish_wizard is not None:
            offering_id = self.wfs_publish_wizard.get_offering_id()
            if offering_id:
                self.select_offering.emit(offering_id)
            self.wfs_publish_wizard.deleteLater()
            self.wfs_publish_wizard = None

    def _load_generation_report(self) -> None:
        """
        Define displayed stored data

        Args:
            stored_data: StoredData
        """
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self.clear_layout(self.vlayout_execution)
        self._add_upload_log(self._stored_data)
        self._add_vectordb_stored_data_logs(self._stored_data)
        self._add_stored_data_execution_logs(self._stored_data)
        QGuiApplication.restoreOverrideCursor()

    def _set_stored_data_details(self, stored_data: StoredData) -> None:
        """
        Define stored data details

        Args:
            stored_data: (StoredData)
        """
        status = stored_data.status
        self.lbl_status_icon.setText("")
        self.lbl_status_icon.setPixmap(self._get_status_icon(status))
        self.lbl_status.setText(self._get_status_text(stored_data))

        self.lne_name.setText(stored_data.name)
        self.lne_id.setText(stored_data._id)
        self.mdl_stored_data_details.set_stored_data(stored_data)
        self.gpx_data_structure.setVisible(len(stored_data.get_tables()) != 0)
        self.mdl_table_relation.set_stored_data_tables(stored_data)
        vlayer = stored_data.create_extent_layer()
        self.gpx_data_extent.setVisible(vlayer.isValid())

    def _add_extent_layer(self) -> None:
        """
        Slot called for extent layer add in canvas

        """
        if self._stored_data:
            vlayer = self._stored_data.create_extent_layer()
            if vlayer.isValid():
                QgsProject.instance().addMapLayer(vlayer)

    def _add_upload_log(self, stored_data: StoredData) -> None:
        """
        Add log for stored data upload if defined

        Args:
            stored_data: StoredData
        """
        if stored_data.tags and "upload_id" in stored_data.tags:
            upload_id = stored_data.tags["upload_id"]

            try:
                manager = UploadRequestManager()
                upload = manager.get_upload(stored_data.datastore_id, upload_id)
                widget = UploadLogWidget(self)
                widget.set_upload(upload)
                self.vlayout_execution.addWidget(widget)
            except UnavailableUploadException as exc:
                self.log(
                    self.tr("Can't define upload logs : {0}").format(exc), push=True
                )

    def _add_vectordb_stored_data_logs(self, stored_data: StoredData) -> None:
        """
        Add log for stored data vector db if defined

        Args:
            stored_data: StoredData
        """
        if stored_data.tags and "vectordb_id" in stored_data.tags:
            vectordb_id = stored_data.tags["vectordb_id"]
            try:
                manager = StoredDataRequestManager()
                vectordb_stored_data = manager.get_stored_data(
                    datastore_id=stored_data.datastore_id, stored_data_id=vectordb_id
                )
                self._add_stored_data_execution_logs(vectordb_stored_data)
            except ReadStoredDataException as exc:
                self.log(
                    self.tr("Can't define execution logs : {0}").format(exc), push=True
                )

    def _add_stored_data_execution_logs(self, stored_data: StoredData) -> None:
        """
        Add log for stored data execution

        Args:
            stored_data: StoredData
        """
        try:
            manager = ProcessingRequestManager()
            executions = manager.get_stored_data_executions(
                datastore_id=stored_data.datastore_id, stored_data_id=stored_data._id
            )
            for execution in executions:
                widget = ExecutionLogWidget(stored_data.datastore_id, self)
                widget.set_processing_execution(execution)
                self.vlayout_execution.addWidget(widget)
        except UnavailableExecutionException as exc:
            self.log(
                self.tr("Can't define execution logs : {0}").format(exc), push=True
            )

    def _get_status_text(self, stored_data: StoredData) -> str:
        """
        Define status text from a stored data

        Args:
            stored_data: (StoredData) stored data

        Returns: status text

        """
        status = stored_data.status
        if status == StoredDataStatus.CREATED:
            result = self.tr(
                "Waiting for data creation. You will find above technical information about executing "
                "processing."
            )
        elif status == StoredDataStatus.GENERATING:
            result = self.tr(
                "Data is generating. You will find above technical information about executing processing."
            )
        elif status == StoredDataStatus.UNSTABLE:
            if stored_data.type == "VECTOR-DB":
                result = self.tr("Database integration failed.")
            else:
                result = self.tr("Tile creation failed.")
            result += self.tr(
                " You will find above technical information about processing executed and encountered "
                "problem."
            )
        elif status == StoredDataStatus.MODIFYING:
            result = self.tr(
                "Data is generating. You will find above technical information about executing processing."
            )
        else:
            # GENERATED and DELETED
            if stored_data.type == StoredDataType.VECTORDB:
                result = self.tr("Database integration successful.")
            else:
                result = self.tr("Tile creation successful.")
            result += self.tr(
                " You will find above technical information about executed processing."
            )
        return result

    @staticmethod
    def _get_status_icon(status: StoredDataStatus) -> QPixmap:
        """
        Get status icon

        Args:
            status: StoredDataStatus

        Returns: QPixmap

        """
        if status == StoredDataStatus.CREATED:
            result = QIcon(QgsApplication.iconPath("mTaskQueued.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == StoredDataStatus.GENERATING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == StoredDataStatus.UNSTABLE:
            result = QIcon(QgsApplication.iconPath("mIconWarning.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == StoredDataStatus.MODIFYING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        else:
            # GENERATED and DELETED
            result = QIcon(QgsApplication.iconPath("mIconSuccess.svg")).pixmap(
                QSize(16, 16)
            )

        return result
