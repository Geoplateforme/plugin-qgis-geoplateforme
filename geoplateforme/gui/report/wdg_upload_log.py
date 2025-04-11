# standard
import os

# PyQGIS
from qgis.core import QgsApplication
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import QAbstractItemView, QWidget

# plugin
from geoplateforme.api.custom_exceptions import UnavailableUploadException
from geoplateforme.api.upload import Upload, UploadRequestManager, UploadStatus
from geoplateforme.gui.report.mdl_upload_details import UploadDetailsTreeModel
from geoplateforme.gui.report.wdg_execution_log import ExecutionLogWidget
from geoplateforme.toolbelt import PlgLogger


class UploadLogWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        """
        QWidget to display dashboard

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_upload_log.ui"),
            self,
        )
        self.mdl_upload_details = UploadDetailsTreeModel(self)
        self.trv_upload_details.setModel(self.mdl_upload_details)
        self.trv_upload_details.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

    def set_upload(self, upload: Upload) -> None:
        """
        Define visible upload

        Args:
            upload: (Upload)
        """
        status = UploadStatus(upload.status)
        self.lbl_status.setPixmap(self._get_status_icon(status))
        self.mdl_upload_details.set_upload(upload)

        try:
            manager = UploadRequestManager()
            executions = manager.get_upload_checks_execution(
                datastore=upload.datastore_id, upload=upload.id
            )
            for execution in executions:
                widget = ExecutionLogWidget(upload.datastore_id, self)
                widget.set_check_execution(execution)
                self.vlayout_checks.addWidget(widget)
        except UnavailableUploadException as exc:
            self.log(
                self.tr("Can't define execution logs : {0}").format(exc), push=True
            )

    @staticmethod
    def _get_status_icon(status: UploadStatus) -> QPixmap:
        if status == UploadStatus.CREATED:
            result = QIcon(QgsApplication.iconPath("mTaskQueued.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == UploadStatus.GENERATING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        elif status == UploadStatus.UNSTABLE:
            result = QIcon(QgsApplication.iconPath("mIconWarning.svg")).pixmap(
                QSize(16, 16)
            )
        else:
            result = QIcon(QgsApplication.iconPath("mIconSuccess.svg")).pixmap(
                QSize(16, 16)
            )
        return result
