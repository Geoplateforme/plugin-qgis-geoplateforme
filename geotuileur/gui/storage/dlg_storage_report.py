import json
import os
import tempfile

from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QProgressBar,
    QTableView,
    QWidget,
)

from geotuileur.__about__ import __title_clean__
from geotuileur.api.datastore import DatastoreRequestManager
from geotuileur.api.stored_data import StorageType, StoredData
from geotuileur.gui.mdl_stored_data import StoredDataListModel
from geotuileur.gui.proxy_model_stored_data import StoredDataProxyModel
from geotuileur.gui.report.dlg_report import ReportDialog
from geotuileur.processing import GeotuileurProvider
from geotuileur.processing.delete_data import DeleteDataAlgorithm
from geotuileur.toolbelt import PlgLogger


class StorageReportDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        """
        QDialog to display storage report

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "dlg_storage_report.ui"),
            self,
        )

        # Create model for stored data display
        self.mdl_stored_data = StoredDataListModel(self)

        # Create proxy model for each table

        # Data integrated in database
        self._init_table_view(
            self.tbv_integrated_in_database,
            visible_storage=[
                StorageType.POSTGRESQL,
                StorageType.POSTGRESQL_DYN,
            ],
        )
        # Data integrated as file
        self._init_table_view(
            self.tbv_integrated_as_file, visible_storage=[StorageType.FILESYSTEM]
        )

        # Data integrated as S3
        self._init_table_view(
            self.tbv_integrated_as_s3, visible_storage=[StorageType.S3]
        )

        self.cbx_datastore.currentIndexChanged.connect(self._datastore_updated)
        self._datastore_updated()

    def refresh(self):
        """
        Force refresh of stored data model

        """
        self._datastore_updated()

    def _init_table_view(self, tbv: QTableView, visible_storage: [StorageType]) -> None:
        """
        Initialization of a table view for specific storage type visibility

        Args:
            tbv:  QTableView table view
            visible_storage: [StorageType] visible storage type
        """
        # Create proxy mode
        proxy_mdl = self._create_proxy_model(visible_storage=visible_storage)
        tbv.setModel(proxy_mdl)

        tbv.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        # Remove vertical header and disable edit
        tbv.verticalHeader().setVisible(False)
        tbv.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Remove some columns
        tbv.setColumnHidden(self.mdl_stored_data.STATUS_COL, True)
        tbv.setColumnHidden(self.mdl_stored_data.ACTION_COL, True)
        tbv.setColumnHidden(self.mdl_stored_data.OTHER_ACTIONS_COL, True)

        # Connection for delete and report actions
        tbv.clicked.connect(lambda index: self._item_clicked(index, proxy_mdl))

    def _create_proxy_model(
        self,
        visible_storage: [StorageType],
    ) -> StoredDataProxyModel:
        """
        Create StoredDataProxyModel with filters

        Args:
            visible_storage: [StorageType] visible stored data storage type

        Returns: StoredDataProxyModel

        """
        proxy_mdl = StoredDataProxyModel(self)
        proxy_mdl.setSourceModel(self.mdl_stored_data)

        proxy_mdl.set_visible_storage_type(visible_storage)

        return proxy_mdl

    def _datastore_updated(self) -> None:
        """
        Update stored data combobox when datastore is updated

        """
        datastore_id = self.cbx_datastore.current_datastore_id()
        if datastore_id:
            self.mdl_stored_data.set_datastore(
                self.cbx_datastore.current_datastore_id()
            )

            self.tbv_integrated_in_database.resizeRowsToContents()
            self.tbv_integrated_in_database.resizeColumnsToContents()

            try:
                manager = DatastoreRequestManager()
                datastore = manager.get_datastore(datastore_id)

                (use, quota) = datastore.get_storage_use_and_quota("POSTGRESQL")
                self._update_progress_bar(quota, use, self.pgb_integrated_in_database)

                (use, quota) = datastore.get_storage_use_and_quota("FILESYSTEM")
                self._update_progress_bar(quota, use, self.pgb_integrated_as_file)

                (use, quota) = datastore.get_storage_use_and_quota("S3")
                self._update_progress_bar(quota, use, self.pgb_integrated_as_s3)

            except DatastoreRequestManager.UnavailableDatastoreException as exc:
                self.log(
                    message=self.tr(
                        "Can't define datastore '{0}' from requests : {1}"
                    ).format(datastore_id, exc),
                    log_level=1,
                    push=True,
                )

    @staticmethod
    def _update_progress_bar(quota: int, use: int, pgb: QProgressBar) -> None:

        pgb.setMinimum(0)
        pgb.setMaximum(int(quota / 1e6))
        pgb.setValue(int(use / 1e6))
        pgb.setFormat(f"%p% ({use / 1e6} Mo / {quota / 1e6} Mo)")

    def _item_clicked(
        self, index: QModelIndex, proxy_model: StoredDataProxyModel
    ) -> None:
        """
        Launch action for selected table item depending on clicked column

        Args:
            index: selected index
            proxy_model: used StoredDataProxyModel
        """
        # Get StoredData
        stored_data = proxy_model.data(
            proxy_model.index(index.row(), self.mdl_stored_data.NAME_COL),
            QtCore.Qt.UserRole,
        )
        if stored_data:
            if index.column() == self.mdl_stored_data.DELETE_COL:
                self._delete(stored_data)
            elif index.column() == self.mdl_stored_data.REPORT_COL:
                self._show_report(stored_data)

    def _delete(self, stored_data: StoredData) -> None:
        """
        Delete a stored data

        Args:
            stored_data: (StoredData) stored data to delete
        """

        data = {
            DeleteDataAlgorithm.DATASTORE: stored_data.datastore_id,
            DeleteDataAlgorithm.STORED_DATA: stored_data.id,
        }
        filename = tempfile.NamedTemporaryFile(
            prefix=f"qgis_{__title_clean__}_", suffix=".json"
        ).name
        with open(filename, "w") as file:
            json.dump(data, file)
        algo_str = f"{GeotuileurProvider().id()}:{DeleteDataAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)
        params = {DeleteDataAlgorithm.INPUT_JSON: filename}
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        result, success = alg.run(parameters=params, context=context, feedback=feedback)

        if success:
            row = self.mdl_stored_data.get_stored_data_row(stored_data.id)
            self.mdl_stored_data.removeRow(row)
        else:
            self.log(
                self.tr("Stored data {0} delete error : {1}").format(
                    stored_data.id, feedback.textLog()
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
