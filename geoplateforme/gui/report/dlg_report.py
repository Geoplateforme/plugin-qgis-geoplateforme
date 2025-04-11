import os

from qgis.core import QgsApplication, QgsProject
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QHeaderView, QWidget

from geoplateforme.api.custom_exceptions import (
    UnavailableExecutionException,
    UnavailableStoredData,
    UnavailableUploadException,
)
from geoplateforme.api.processing import ProcessingRequestManager
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataRequestManager,
    StoredDataStatus,
)
from geoplateforme.api.upload import UploadRequestManager
from geoplateforme.gui.mdl_table_relation import TableRelationTreeModel
from geoplateforme.gui.report.mdl_stored_data_details import StoredDataDetailsModel
from geoplateforme.gui.report.wdg_execution_log import ExecutionLogWidget
from geoplateforme.gui.report.wdg_upload_log import UploadLogWidget
from geoplateforme.toolbelt import PlgLogger


class ReportDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        """
        QDialog to display report for a stored data

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "dlg_report.ui"),
            self,
        )

        self.setWindowTitle(self.tr("Report"))

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

    def set_stored_data(self, stored_data: StoredData) -> None:
        """
        Define displayed stored data

        Args:
            stored_data: StoredData
        """
        self._stored_data = stored_data
        self._set_stored_data_details(stored_data)
        self._add_upload_log(stored_data)
        self._add_vectordb_stored_data_logs(stored_data)
        self._add_stored_data_execution_logs(stored_data)

    def _set_stored_data_details(self, stored_data: StoredData) -> None:
        """
        Define stored data details

        Args:
            stored_data: (StoredData)
        """
        status = StoredDataStatus[stored_data.status]
        self.lbl_status_icon.setText("")
        self.lbl_status_icon.setPixmap(self._get_status_icon(status))
        self.lbl_status.setText(self._get_status_text(stored_data))

        self.lne_name.setText(stored_data.name)
        self.lne_id.setText(stored_data.id)
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
                    datastore=stored_data.datastore_id, stored_data=vectordb_id
                )
                self._add_stored_data_execution_logs(vectordb_stored_data)
            except UnavailableStoredData as exc:
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
                datastore=stored_data.datastore_id, stored_data=stored_data.id
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
        status = StoredDataStatus[stored_data.status]
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
            if stored_data.type == "VECTOR-DB":
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
