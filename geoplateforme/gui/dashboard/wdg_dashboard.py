import json
import os
import tempfile
from typing import List, Optional

from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorTileLayer,
)
from qgis.gui import QgsMetadataWidget
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QItemSelectionModel,
    QModelIndex,
)
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QAction,
    QLabel,
    QMenu,
    QMessageBox,
    QTableView,
    QWidget,
)

from geoplateforme.__about__ import __title_clean__
from geoplateforme.api.custom_exceptions import (
    ReadMetadataException,
    UnavailableMetadataFileException,
)
from geoplateforme.api.metadata import MetadataRequestManager
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataStatus,
    StoredDataStep,
    StoredDataType,
)
from geoplateforme.gui.dashboard.dlg_stored_data_details import StoredDataDetailsDialog
from geoplateforme.gui.dashboard.wdg_service_details import ServiceDetailsWidget
from geoplateforme.gui.dashboard.wdg_upload_details import UploadDetailsWidget
from geoplateforme.gui.mdl_offering import OfferingListModel
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
from geoplateforme.gui.upload_creation.wzd_upload_creation import UploadCreationWizard
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.delete_stored_data import DeleteStoredDataAlgorithm
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
        self.wdg_metadata = None
        self._set_metadata_view()

        # Create model for upload display
        self.mdl_upload = UploadListModel(self)

        # Create model for stored data display
        self.mdl_stored_data = StoredDataListModel(self)

        # Create model for offering display
        self.mdl_offering = OfferingListModel(self)

        # List of table view
        self.tbv_list = []

        # Initialize upload table view
        self.tbv_upload.setModel(self.mdl_upload)
        self.tbv_upload.verticalHeader().setVisible(False)
        self.tbv_upload.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_list.append(self.tbv_upload)
        self.tbv_upload.pressed.connect(
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

        # Initialize service table view
        self.tbv_service.setModel(self.mdl_offering)
        self.tbv_service.verticalHeader().setVisible(False)
        self.tbv_service.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.tbv_service.pressed.connect(self._service_clicked)

        # remove detail zone
        self.detail_dialog = None
        self.remove_detail_zone()

        self.service_detail_dialog = None
        self.remove_service_detail_zone()

        self.import_wizard = None

        self.cbx_datastore.currentIndexChanged.connect(self._datastore_updated)
        self.cbx_dataset.activated.connect(self._dataset_updated)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_refresh.setIcon(QIcon(":/images/themes/default/mActionRefresh.svg"))

        self.btn_create.clicked.connect(self._create_dataset)
        self.btn_create.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))

        self.btn_add_data.clicked.connect(self._add_data_to_dataset)
        self.btn_add_data.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))

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
        tbv.pressed.connect(lambda index: self._item_clicked(index, proxy_mdl, tbv))

    def _set_metadata_view(self) -> None:
        """
        Create metadata view when metadata is present
        """
        if self.wdg_metadata:
            self.metadata_layout.removeWidget(self.wdg_metadata)
            self.wdg_metadata = None

        datastore_id = self.cbx_datastore.current_datastore_id()
        dataset_name = self.cbx_dataset.current_dataset_name()

        metadatas = []
        manager = MetadataRequestManager()
        if datastore_id and dataset_name:
            tags = {"datasheet_name": dataset_name}
            metadatas = manager._get_metadata_list(datastore_id=datastore_id, tags=tags)
        metadata = None
        if len(metadatas) == 1:
            try:
                metadata = metadatas[0].to_qgis_format()
                self.wdg_metadata = QgsMetadataWidget()
                self.wdg_metadata.setMetadata(metadata)
                self.wdg_metadata.setMode(QgsMetadataWidget.Mode.LayerMetadata)
            except UnavailableMetadataFileException as exc:
                self.log(
                    f"Error while getting Metadata informations: {exc}",
                    log_level=2,
                    push=False,
                )
            except ReadMetadataException as exc:
                self.log(
                    f"Error while reading Metadata informations: {exc}",
                    log_level=2,
                    push=False,
                )
        if metadata is None:
            self.wdg_metadata = QLabel()
            self.wdg_metadata.setText("No metadata available")
        self.metadata_layout.addWidget(self.wdg_metadata)

    def refresh(
        self, datastore_id: Optional[str] = None, dataset_name: Optional[str] = None
    ) -> None:
        """
        Force refresh of stored data model

        """
        # Disable refresh button : must processEvents so user can't click while updating
        self.btn_refresh.setEnabled(False)
        if not datastore_id:
            datastore_id = self.cbx_datastore.current_datastore_id()
        if not dataset_name:
            dataset_name = self.cbx_dataset.current_dataset_name()

        QCoreApplication.processEvents()

        # Diconnect signals
        self.cbx_datastore.currentIndexChanged.disconnect(self._datastore_updated)
        self.cbx_dataset.activated.disconnect(self._dataset_updated)

        # Update datastore content
        self.cbx_datastore.refresh()
        self.cbx_datastore.set_datastore_id(datastore_id)
        self._datastore_updated(force_refresh=True)
        self.cbx_dataset.set_dataset_name(dataset_name)
        self._dataset_updated()

        # Connect signals
        self.cbx_datastore.currentIndexChanged.connect(self._datastore_updated)
        self.cbx_dataset.activated.connect(self._dataset_updated)

        # Enable new refresh
        self.btn_refresh.setEnabled(True)

    def _service_clicked(self, index: QModelIndex) -> None:
        """Display service details when clicked

        :param index: clicked index
        :type index: QModelIndex
        """
        # Hide detail zone
        self.remove_service_detail_zone()
        offering = self.mdl_offering.data(
            self.mdl_offering.index(index.row(), 0),
            QtCore.Qt.UserRole,
        )
        if offering:
            self.service_detail_dialog = ServiceDetailsWidget(self)
            self.service_detail_dialog.set_offering(
                offering, self.cbx_dataset.current_dataset_name()
            )
            self.service_detail_dialog.select_stored_data.connect(
                self.select_stored_data
            )
            self.service_detail_widget_layout.addWidget(self.service_detail_dialog)
            self.service_detail_zone.show()

    def select_upload(self, upload_id: str, refresh: bool = True) -> None:
        """Select upload in table view

        :param upload_id: upload id
        :type upload_id: str
        :param refresh: force refresh before selection, defaults to True
        :type refresh: bool, optional
        """
        if refresh:
            self.refresh()

        self.tabWidget.setCurrentWidget(self.tab_dataset)

        row = self.mdl_upload.get_upload_row(upload_id=upload_id)
        if row != -1:
            self.mdl_upload.index(row, self.mdl_upload.NAME_COL)

            # Get proxy model index for selection
            index = self.mdl_upload.index(row, self.mdl_upload.NAME_COL)

            # Update selection model
            self.tbv_upload.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            self._item_clicked(index, self.tbv_upload.model(), self.tbv_upload)

    def select_stored_data(self, stored_data_id: str, refresh: bool = True) -> None:
        """Select stored data in table view

        :param stored_data_id: stored data id
        :type stored_data_id: str
        :param refresh: force refresh before selection, defaults to True
        :type refresh: bool, optional
        """
        if refresh:
            self.refresh()
        row = self.mdl_stored_data.get_stored_data_row(stored_data_id=stored_data_id)

        self.tabWidget.setCurrentWidget(self.tab_dataset)

        if row != -1:
            # Check all stored data table view
            for tbv in [
                self.tbv_vector_db,
                self.tbv_pyramid_vector,
                self.tbv_pyramid_raster,
            ]:
                # Get proxy model index for selection
                index = tbv.model().mapFromSource(
                    self.mdl_stored_data.index(row, self.mdl_stored_data.NAME_COL)
                )
                if index.isValid():
                    tbv.selectionModel().select(
                        index,
                        QItemSelectionModel.SelectionFlag.Select
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
                    self._item_clicked(index, tbv.model(), tbv)
                    break

    def select_offering(self, offerring_id: str, refresh: bool = True) -> None:
        """Select offering in table view

        :param offerring_id: offering id
        :type offerring_id: str
        :param refresh: force refresh before selection, defaults to True
        :type refresh: bool, optional
        """
        if refresh:
            self.refresh()

        self.tabWidget.setCurrentWidget(self.tab_service)

        row = self.mdl_offering.get_offering_row(offering_id=offerring_id)

        if row != -1:
            self.mdl_offering.index(row, self.mdl_offering.NAME_COL)

            # Get proxy model index for selection
            index = self.mdl_offering.index(row, self.mdl_offering.NAME_COL)

            # Update selection model
            self.tbv_service.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            self._service_clicked(index)

    def _item_clicked(
        self, index: QModelIndex, model: QAbstractItemModel, tbv: QTableView
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
        # Hide detail zone
        self.remove_detail_zone()
        # Get StoredData
        item = model.data(
            model.index(index.row(), 0),
            QtCore.Qt.UserRole,
        )
        if item:
            if isinstance(model, StoredDataProxyModel):
                self.detail_dialog = StoredDataDetailsDialog(self)
                self.detail_dialog.set_stored_data(item)
                self.detail_widget_layout.addWidget(self.detail_dialog)
                self.detail_dialog.select_stored_data.connect(self.select_stored_data)
                self.detail_dialog.select_offering.connect(self.select_offering)
                self.detail_dialog.stored_data_deleted.connect(
                    self._stored_data_deleted
                )
                self.detail_zone.show()
            elif isinstance(model, UploadListModel):
                self.detail_dialog = UploadDetailsWidget(self)
                self.detail_dialog.set_upload(item)
                self.detail_widget_layout.addWidget(self.detail_dialog)
                self.detail_dialog.select_stored_data.connect(self.select_stored_data)
                self.detail_dialog.upload_deleted.connect(self._upload_deleted)
                self.detail_zone.show()

    def _stored_data_deleted(self, stored_data_id: str) -> None:
        """Refresh dataset after stored data delete

        :param stored_data_id: deleted stored data id
        :type stored_data_id: str
        """
        self._dataset_updated()

    def _upload_deleted(self, upload_id: str) -> None:
        """Refresh dataset after upload delete

        :param upload_id: deleted upload id
        :type upload_id: str
        """
        self._dataset_updated()

    def remove_detail_zone(self) -> None:
        """Hide detail zone and remove attached widgets"""
        # Hide detail zone
        self.detail_zone.hide()
        if self.detail_dialog:
            self.detail_widget_layout.removeWidget(self.detail_dialog)
            self.detail_dialog = None

    def remove_service_detail_zone(self) -> None:
        """Hide detail zone for service and remove attached widgets"""
        self.service_detail_zone.hide()
        if self.service_detail_dialog:
            self.service_detail_widget_layout.removeWidget(self.service_detail_dialog)
            self.service_detail_dialog = None

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
            params = {
                DeleteStoredDataAlgorithm.DATASTORE: stored_data.datastore_id,
                DeleteStoredDataAlgorithm.STORED_DATA: stored_data._id,
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteStoredDataAlgorithm().name()}"
            )
            alg = QgsApplication.processingRegistry().algorithmById(algo_str)
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
        # TODO : tag tms_url can't be used in stored data because of a 99 char limits
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

    def _create_dataset(self) -> None:
        """
        Show upload creation wizard with current datastore

        """
        if self.import_wizard is None:
            self.import_wizard = UploadCreationWizard(
                self, self.cbx_datastore.current_datastore_id()
            )
            self.import_wizard.finished.connect(self._del_import_wizard)
        self.import_wizard.show()

    def _add_data_to_dataset(self) -> None:
        """
        Show upload creation wizard with current datastore and dataset

        """
        if self.import_wizard is None:
            self.import_wizard = UploadCreationWizard(
                self,
                self.cbx_datastore.current_datastore_id(),
                self.cbx_dataset.current_dataset_name(),
            )
            self.import_wizard.finished.connect(self._del_import_wizard)
        self.import_wizard.show()

    def _del_import_wizard(self) -> None:
        """
        Delete import wizard

        """
        if self.import_wizard is not None:
            self.refresh(
                datastore_id=self.import_wizard.get_datastore_id(),
                dataset_name=self.import_wizard.get_dataset_name(),
            )
            created_upload_id = self.import_wizard.get_created_upload_id()
            created_stored_data_id = self.import_wizard.get_created_stored_data_id()
            if created_stored_data_id:
                self.select_stored_data(created_stored_data_id, False)
            elif created_upload_id:
                self.select_upload(created_upload_id, False)
            self.import_wizard.deleteLater()
            self.import_wizard = None

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

    def _datastore_updated(self, index: int = 0, force_refresh: bool = False) -> None:
        """
        Update stored data combobox when datastore is updated

        """
        self.cbx_dataset.set_datastore_id(
            self.cbx_datastore.current_datastore_id(), force_refresh
        )

    def _dataset_updated(self) -> None:
        """
        Update stored data combobox when dataset is updated

        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))

        # remove detail zone
        self.remove_detail_zone()
        self.remove_service_detail_zone()

        self._set_metadata_view()

        self.mdl_upload.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.mdl_stored_data.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.mdl_offering.set_datastore(
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

        # For now only do a simple resize of columns
        self.tbv_service.resizeColumnsToContents()

        QGuiApplication.restoreOverrideCursor()
