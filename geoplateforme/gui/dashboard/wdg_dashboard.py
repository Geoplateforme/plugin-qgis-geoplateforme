import json
import os
import tempfile
from typing import List

from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorTileLayer,
)
from qgis.gui import QgsMetadataWidget
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QCoreApplication, QModelIndex
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon, QStandardItemModel
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QAction,
    QMenu,
    QMessageBox,
    QTableView,
    QWidget,
)

from geoplateforme.__about__ import __title_clean__
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataStatus,
    StoredDataStep,
    StoredDataType,
)
from geoplateforme.gui.mdl_stored_data import StoredDataListModel
from geoplateforme.gui.mdl_upload import UploadListModel
from geoplateforme.gui.proxy_model_stored_data import StoredDataProxyModel
from geoplateforme.gui.publication_creation.wzd_publication_creation import (
    PublicationFormCreation,
)
from geoplateforme.gui.report.dlg_report import ReportDialog
from geoplateforme.gui.tile_creation.wzd_tile_creation import TileCreationWizard
from geoplateforme.gui.update_publication.wzd_update_publication import (
    UpdatePublicationWizard,
)
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.delete_data import DeleteDataAlgorithm
from geoplateforme.processing.unpublish import UnpublishAlgorithm
from geoplateforme.toolbelt import PlgLogger


class DashboardWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        """
        QWidget to display dashboard

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_dashboard.ui"),
            self,
        )

        # Add metadata widget
        self.metadata = QgsMetadataWidget()
        self.metadata.setMode(QgsMetadataWidget.Mode.ProjectMetadata)
        self.metadata_layout.addWidget(self.metadata)

        # Create model for upload display
        self.mdl_upload = UploadListModel(self)

        # Create model for stored data display
        self.mdl_stored_data = StoredDataListModel(self)

        # List of table view
        self.tbv_list = []

        # Initialize upload table view
        self.tbv_upload.setModel(self.mdl_upload)
        self.tbv_upload.verticalHeader().setVisible(False)
        self.tbv_upload.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_list.append(self.tbv_upload)
        self.tbv_upload.clicked.connect(
            lambda index: self._item_clicked(index, self.mdl_upload, self.tbv_upload)
        )

        # Create proxy model for each table
        # Vector DB
        self._init_table_view(
            tbv=self.tbv_vector_db,
            filter_type=[StoredDataType.VECTORDB],
            visible_steps=[],
            visible_status=[],
        )
        self.tbv_list.append(self.tbv_vector_db)

        # Pyramids vector
        self._init_table_view(
            tbv=self.tbv_pyramid_vector,
            filter_type=[StoredDataType.PYRAMIDVECTOR],
            visible_steps=[],
            visible_status=[],
        )
        self.tbv_list.append(self.tbv_pyramid_vector)

        # Pyramids raster
        self._init_table_view(
            tbv=self.tbv_pyramid_raster,
            filter_type=[StoredDataType.PYRAMIDRASTER],
            visible_steps=[],
            visible_status=[],
        )
        self.tbv_list.append(self.tbv_pyramid_raster)

        self.cbx_datastore.currentIndexChanged.connect(self._datastore_updated)
        self.cbx_dataset.activated.connect(self._dataset_updated)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_refresh.setIcon(QIcon(":/images/themes/default/mActionRefresh.svg"))

        self.btn_create.clicked.connect(self._create)
        self.btn_create.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))

        self._datastore_updated()

    def _init_table_view(
        self,
        tbv: QTableView,
        filter_type: List[StoredDataType],
        visible_steps: List[StoredDataStep],
        visible_status: List[StoredDataStatus],
    ) -> None:
        """
        Initialization of a table view for specific stored data steps and status visibility

        Args:
            tbv:  QTableView table view
            filter_type: List[StoredDataType] visible types
            visible_steps: List[StoredDataStep] visible stored data steps
            visible_status: List[StoredDataStatus] visible stored data status
        """
        proxy_mdl = self._create_proxy_model(
            filter_type=filter_type,
            visible_steps=visible_steps,
            visible_status=visible_status,
        )
        tbv.setModel(proxy_mdl)
        tbv.verticalHeader().setVisible(False)
        tbv.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbv.clicked.connect(
            lambda index: self._item_clicked(index, self.mdl_stored_data, tbv)
        )

    def refresh(self) -> None:
        """
        Force refresh of stored data model

        """
        # Disable refresh button : must processEvents so user can't click while updating
        self.btn_refresh.setEnabled(False)
        QCoreApplication.processEvents()

        # Update datastore content
        self.cbx_datastore.refresh()
        self._datastore_updated()

        # Enable new refresh
        self.btn_refresh.setEnabled(True)

    def _item_clicked(
        self, index: QModelIndex, model: QStandardItemModel, tbv: QTableView
    ) -> None:
        """
        Launch action for selected table item depending on clicked column

        Args:
            index: selected index
            proxy_model: used StoredDataProxyModel
        """
        # Remove other selections
        for table in self.tbv_list:
            if table != tbv:
                table.clearSelection()
        # Get StoredData
        item = model.data(
            model.index(index.row(), model.NAME_COL),
            QtCore.Qt.UserRole,
        )
        if item:
            print("affiche detail")

    def _stored_data_main_action(self, stored_data: StoredData):
        """
        Execute stored data main action depending on current stored data status and step

        Args:
            stored_data: (StoredData) stored data
        """
        status = StoredDataStatus[stored_data.status]
        if status == StoredDataStatus.GENERATING:
            self._show_report(stored_data)
        elif status == StoredDataStatus.GENERATED:
            current_step = stored_data.get_current_step()
            if current_step == StoredDataStep.TILE_GENERATION:
                self._generate_tile_wizard(stored_data)
            elif current_step == StoredDataStep.TILE_SAMPLE:
                self._tile_sample_wizard(stored_data)
            elif current_step == StoredDataStep.TILE_UPDATE:
                self._compare(stored_data)
            elif current_step == StoredDataStep.TILE_PUBLICATION:
                self._publish_wizard(stored_data)
            elif current_step == StoredDataStep.PUBLISHED:
                self._view_tile(stored_data)
        else:
            self._show_report(stored_data)

    def _stored_data_other_actions(self, stored_data: StoredData):
        """
        Display menu for other actions on stored data

        Args:
            stored_data: (StoredData) stored data
        """
        if stored_data.get_current_step() == StoredDataStep.PUBLISHED:
            menu = QMenu(self)

            replace_action = QAction(self.tr("Replace data"))
            replace_action.triggered.connect(
                lambda: self._replace_data_wizard(stored_data)
            )
            menu.addAction(replace_action)

            style_action = QAction(self.tr("Manage styles"))
            style_action.triggered.connect(lambda: self._style_wizard(stored_data))
            menu.addAction(style_action)

            update_publish_action = QAction(self.tr("Update publication informations"))
            update_publish_action.triggered.connect(
                lambda: self._publish_info_update_wizard(stored_data)
            )
            menu.addAction(update_publish_action)

            unpublish_action = QAction(self.tr("Unpublish"))
            unpublish_action.triggered.connect(lambda: self._unpublish(stored_data))
            menu.addAction(unpublish_action)

            menu.exec(QCursor.pos())

    def _delete(self, stored_data: StoredData) -> None:
        """
        Delete a stored data

        Args:
            stored_data: (StoredData) stored data to delete
        """

        reply = QMessageBox.question(
            self,
            "Delete data",
            "Are you sure you want to delete the data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            data = {
                DeleteDataAlgorithm.DATASTORE: stored_data.datastore_id,
                DeleteDataAlgorithm.STORED_DATA: stored_data._id,
            }
            filename = tempfile.NamedTemporaryFile(
                prefix=f"qgis_{__title_clean__}_", suffix=".json"
            ).name
            with open(filename, "w") as file:
                json.dump(data, file)
            algo_str = f"{GeoplateformeProvider().id()}:{DeleteDataAlgorithm().name()}"
            alg = QgsApplication.processingRegistry().algorithmById(algo_str)
            params = {DeleteDataAlgorithm.INPUT_JSON: filename}
            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()
            result, success = alg.run(
                parameters=params, context=context, feedback=feedback
            )
            if success:
                row = self.mdl_stored_data.get_stored_data_row(stored_data._id)
                self.mdl_stored_data.removeRow(row)

            else:
                self.log(
                    self.tr("delete data error").format(
                        stored_data._id, feedback.textLog()
                    ),
                    log_level=1,
                    push=True,
                )

    def _show_report(self, stored_data: StoredData) -> None:
        """
        Show report for a stored data

        Args:
            stored_data: (StoredData) stored data to publish
        """
        dialog = ReportDialog(self)
        dialog.set_stored_data(stored_data)
        dialog.show()

    def _tile_sample_wizard(self, stored_data: StoredData) -> None:
        """
        Show tile sample wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to view tile sample wizard
        """
        self.log("Tile sample wizard not implemented yet", push=True)

    def _generate_tile_wizard(self, stored_data: StoredData) -> None:
        """
        Show tile generation wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to generate tile
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        publication_wizard = TileCreationWizard(self)
        publication_wizard.set_datastore_id(stored_data.datastore_id)
        publication_wizard.set_stored_data_id(stored_data._id)
        QGuiApplication.restoreOverrideCursor()
        publication_wizard.show()

    def _publish_wizard(self, stored_data: StoredData) -> None:
        """
        Show publish wizard for a stored data

        Args:
            stored_data: (StoredData) stored data to publish
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        publication_wizard = PublicationFormCreation(self)
        publication_wizard.set_datastore_id(stored_data.datastore_id)
        publication_wizard.set_stored_data_id(stored_data._id)
        QGuiApplication.restoreOverrideCursor()
        publication_wizard.show()

    def _view_tile(self, stored_data: StoredData) -> None:
        """
        View tile for a stored data

        Args:
            stored_data: (StoredData) stored data to be viewed
        """
        if stored_data.tags and "tms_url" in stored_data.tags:
            tms_url = stored_data.tags["tms_url"]
            zoom_levels = stored_data.zoom_levels()
            bottom = zoom_levels[-1]
            top = zoom_levels[0]
            layer = QgsVectorTileLayer(
                path=f"type=xyz&url={tms_url}/%7Bz%7D/%7Bx%7D/%7By%7D.pbf&zmax={bottom}&zmin={top}",
                baseName=self.tr("Vector tile : {0}").format(stored_data.name),
            )
            QgsProject.instance().addMapLayer(layer)

    def _replace_data_wizard(self, stored_data: StoredData) -> None:
        """
        Show replace data wizard for a stored data

        Args:
            stored_data: (StoredData) stored data
        """
        self.log("Replace data not implemented yet", push=True)

    def _style_wizard(self, stored_data: StoredData) -> None:
        """
        Show style wizard for a stored data

        Args:
            stored_data: (StoredData) stored data
        """
        self.log("Tile style management not implemented yet", push=True)

    def _publish_info_update_wizard(self, stored_data: StoredData) -> None:
        """
        Show publish information update wizard for a stored data

        Args:
            stored_data: (StoredData) stored data
        """

        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        publication_wizard = UpdatePublicationWizard(self)
        publication_wizard.set_datastore_id(stored_data.datastore_id)
        publication_wizard.set_stored_data_id(stored_data._id)

        QGuiApplication.restoreOverrideCursor()
        publication_wizard.show()

    def _create(self) -> None:
        """
        Show upload creation wizard with current datastore

        """
        QMessageBox.information(
            self,
            "Create new Dataset:",
            "Creating a new Dataset will be avaliable soon !!",
        )

    def _compare(self, stored_data: StoredData) -> None:
        """
        Compare update with initial stored data

        Args:
            stored_data: (StoredData) stored data
        """
        self.log("Compare not implemented yet", push=True)

    def _unpublish(self, stored_data: StoredData) -> None:
        """
        Unpublish a stored data

        Args:
            stored_data: (StoredData) stored data
        """
        reply = QMessageBox.question(
            self,
            "Unpublish",
            "Are you sure you want to unpublish the data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            data = {
                UnpublishAlgorithm.DATASTORE: stored_data.datastore_id,
                UnpublishAlgorithm.STORED_DATA: stored_data._id,
            }
            filename = tempfile.NamedTemporaryFile(
                prefix=f"qgis_{__title_clean__}_", suffix=".json"
            ).name
            with open(filename, "w") as file:
                json.dump(data, file)
            algo_str = f"{GeoplateformeProvider().id()}:{UnpublishAlgorithm().name()}"
            alg = QgsApplication.processingRegistry().algorithmById(algo_str)
            params = {UnpublishAlgorithm.INPUT_JSON: filename}
            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()
            alg.run(parameters=params, context=context, feedback=feedback)
            self.refresh()

            result, success = alg.run(
                parameters=params, context=context, feedback=feedback
            )
            if success:
                self.refresh()
            else:
                self.log(
                    self.tr("Unpublish error ").format(
                        stored_data._id, feedback.textLog()
                    ),
                    log_level=1,
                    push=True,
                )

    def _create_proxy_model(
        self,
        filter_type: List[StoredDataType],
        visible_steps: List[StoredDataStep],
        visible_status: List[StoredDataStatus],
    ) -> StoredDataProxyModel:
        """
        Create StoredDataProxyModel with filters

        Args:
            filter_type: List[StoredDataType] visible types
            visible_steps: List[StoredDataStep] visible stored data steps
            visible_status: List[StoredDataStatus] visible stored data status

        Returns: StoredDataProxyModel

        """
        proxy_mdl = StoredDataProxyModel(self)
        proxy_mdl.setSourceModel(self.mdl_stored_data)

        proxy_mdl.set_filter_type(filter_type)
        proxy_mdl.set_visible_steps(visible_steps)
        proxy_mdl.set_visible_status(visible_status)

        return proxy_mdl

    def _datastore_updated(self) -> None:
        """
        Update stored data combobox when datastore is updated

        """
        self.cbx_dataset.set_datastore_id(self.cbx_datastore.current_datastore_id())

    def _dataset_updated(self) -> None:
        """
        Update stored data combobox when dataset is updated

        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))

        self.mdl_upload.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.mdl_stored_data.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.tbv_upload.resizeRowsToContents()
        # self.tbv_upload.resizeColumnsToContents()

        self.tbv_vector_db.resizeRowsToContents()
        # self.tbv_vector_db.resizeColumnsToContents()

        self.tbv_pyramid_vector.resizeRowsToContents()
        # self.tbv_pyramid_vector.resizeColumnsToContents()

        self.tbv_pyramid_raster.resizeRowsToContents()
        # self.tbv_pyramid_raster.resizeColumnsToContents()

        QGuiApplication.restoreOverrideCursor()
