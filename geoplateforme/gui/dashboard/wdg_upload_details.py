import os

from qgis.core import QgsApplication, QgsProject
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QAction,
    QToolBar,
    QToolButton,
    QWidget,
)

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.upload import Upload, UploadStatus
from geoplateforme.gui.report.mdl_upload_details import UploadDetailsTreeModel
from geoplateforme.gui.report.wdg_upload_log import UploadLogWidget
from geoplateforme.gui.upload_database_integration.wzd_upload_database_integration import (
    UploadDatabaseIntegrationWizard,
)
from geoplateforme.toolbelt import PlgLogger


class UploadDetailsWidget(QWidget):
    select_stored_data = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        """
        QWidget to display report for an upload

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_upload_details.ui"),
            self,
        )

        self.setWindowTitle(self.tr("Details"))

        self._upload = None

        self.mdl_upload_details = UploadDetailsTreeModel(self)
        self.trv_details.setModel(self.mdl_upload_details)
        self.trv_details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.btn_add_extent_layer.pressed.connect(self._add_extent_layer)
        self.btn_load_report.pressed.connect(self._load_generation_report)

        # Add toolbar for stored data actions
        self.edit_toolbar = QToolBar(self)
        self.layout().setMenuBar(self.edit_toolbar)

        self.vector_db_wizard = None

    def set_upload(self, upload: Upload) -> None:
        """
        Define displayed upload

        Args:
            upload: Upload
        """
        self._upload = upload
        self._set_upload_details(upload)

        # Remove all available action in toolbar
        self.edit_toolbar.clear()

        status = upload.status

        if status == UploadStatus.CLOSED:
            generate_vector_db_action = QAction(
                QIcon(str(DIR_PLUGIN_ROOT / "resources/images/dashboard/db.png")),
                self.tr("Génération base de données vectorielle"),
                self,
            )
            generate_vector_db_action.triggered.connect(
                self._show_generate_vector_db_wizard
            )
            button = QToolButton(self)
            button.setDefaultAction(generate_vector_db_action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.edit_toolbar.addWidget(button)

    def _show_generate_vector_db_wizard(self) -> None:
        """Show generate vector db wizard for current upload"""
        self._generate_vector_db_wizard(self._upload)

    def _generate_vector_db_wizard(self, upload: Upload) -> None:
        """
        Show vector db generation wizard for an upload

        Args:
            upload: (Upload) upload to generate vector db
        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))
        self.vector_db_wizard = UploadDatabaseIntegrationWizard(
            datastore_id=upload.datastore_id,
            dataset_name=upload.tags["datasheet_name"],
            upload_id=upload._id,
            upload_name=upload.name,
            parent=self,
        )
        QGuiApplication.restoreOverrideCursor()
        self.vector_db_wizard.finished.connect(self._del_vector_db_wizard)
        self.vector_db_wizard.show()

    def _del_vector_db_wizard(self) -> None:
        """
        Delete vector db wizard

        """
        if self.vector_db_wizard is not None:
            created_stored_data_id = self.vector_db_wizard.get_created_stored_data_id()
            if created_stored_data_id:
                self.select_stored_data.emit(created_stored_data_id)
            self.vector_db_wizard.deleteLater()
            self.vector_db_wizard = None

    def _load_generation_report(self) -> None:
        """
        Load generation report for current upload
        """
        if self._upload:
            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            self._add_upload_log(self._upload)
            QGuiApplication.restoreOverrideCursor()

    def _set_upload_details(self, upload: Upload) -> None:
        """
        Define upload details

        Args:
            upload: (Upload)
        """
        status = upload.status
        self.lbl_status_icon.setText("")
        self.lbl_status_icon.setPixmap(self._get_status_icon(status))
        self.lbl_status.setText(self._get_status_text(upload))

        self.lne_name.setText(upload.name)
        self.lne_id.setText(upload._id)
        self.mdl_upload_details.set_upload(upload)
        vlayer = upload.create_extent_layer()
        self.gpx_data_extent.setVisible(vlayer.isValid())

    def _add_extent_layer(self) -> None:
        """
        Slot called for extent layer add in canvas

        """
        if self._upload:
            vlayer = self._upload.create_extent_layer()
            if vlayer.isValid():
                QgsProject.instance().addMapLayer(vlayer)

    def _add_upload_log(self, upload: Upload) -> None:
        """
        Add log for upload

        Args:
            upload: Upload
        """
        widget = UploadLogWidget(self)
        widget.set_upload(upload)
        self.vlayout_execution.addWidget(widget)

    def _get_status_text(self, upload: Upload) -> str:
        """
        Define status text from an upload

        Args:
            upload: (Upload) upload

        Returns: status text

        """
        status = upload.status
        if status == UploadStatus.CREATED:
            result = self.tr(
                "Waiting for data creation. You will find above technical information about executing "
                "processing."
            )
        elif status == UploadStatus.GENERATING:
            result = self.tr(
                "Data is generating. You will find above technical information about executing processing."
            )
        elif status == UploadStatus.UNSTABLE:
            result = self.tr("Upload integration failed.")
            result += self.tr(
                " You will find above technical information about processing executed and encountered "
                "problem."
            )
        elif status == UploadStatus.MODIFYING:
            result = self.tr(
                "Data is generating. You will find above technical information about executing processing."
            )
        else:
            result = self.tr("Upload creation successful.")
            result += self.tr(
                " You will find above technical information about executed processing."
            )
        return result

    @staticmethod
    def _get_status_icon(status: UploadStatus) -> QPixmap:
        """
        Get status icon

        Args:
            status: UploadStatus

        Returns: QPixmap

        """
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
        elif status == UploadStatus.MODIFYING:
            result = QIcon(QgsApplication.iconPath("mTaskRunning.svg")).pixmap(
                QSize(16, 16)
            )
        else:
            # GENERATED and DELETED
            result = QIcon(QgsApplication.iconPath("mIconSuccess.svg")).pixmap(
                QSize(16, 16)
            )

        return result
