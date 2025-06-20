import os
from typing import List, Optional

from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QItemSelectionModel,
    QModelIndex,
)
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QLabel, QTableView, QWidget

from geoplateforme.api.custom_exceptions import (
    ReadMetadataException,
    UnavailableMetadataFileException,
)
from geoplateforme.api.metadata import MetadataRequestManager
from geoplateforme.api.stored_data import (
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
from geoplateforme.gui.metadata.wdg_metadata_details import MetadataDetailsWidget
from geoplateforme.gui.proxy_model_stored_data import StoredDataProxyModel
from geoplateforme.gui.upload_creation.wzd_upload_creation import UploadCreationWizard
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
        if self.wdg_metadata is not None:
            if isinstance(self.wdg_metadata, MetadataDetailsWidget):
                self.btn_update_metadata.clicked.disconnect(self._update_metadata)
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
                metadata = metadatas[0]
                self.wdg_metadata = MetadataDetailsWidget(
                    metadata=metadata, datastore_id=datastore_id
                )
                self.btn_update_metadata.clicked.connect(self._update_metadata)
                self.btn_update_metadata.show()
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
            self.btn_update_metadata.hide()
        self.metadata_layout.addWidget(self.wdg_metadata)

    def _update_metadata(self):
        """Update metadata"""
        if self.wdg_metadata is not None:
            self.wdg_metadata.update_metadata()

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

            self.service_detail_dialog.offering_deleted.connect(self._offering_deleted)
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

    def _offering_deleted(self, offering_id: str) -> None:
        """Refresh dataset after offering delete

        :param offering_id: deleted offering id
        :type offering_id: str
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

        # Update permission content
        self.wdg_permission.refresh(
            datastore_id=self.cbx_datastore.current_datastore_id()
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
