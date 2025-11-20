import os

from qgis.core import (
    QgsApplication,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
)
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import QSize, Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QAction,
    QLayout,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QWidget,
)

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.custom_exceptions import UploadClosingException
from geoplateforme.api.upload import Upload, UploadRequestManager, UploadStatus
from geoplateforme.gui.report.mdl_upload_details import UploadDetailsTreeModel
from geoplateforme.gui.report.wdg_upload_log import UploadLogWidget
from geoplateforme.gui.upload_database_integration.wzd_upload_database_integration import (
    UploadDatabaseIntegrationWizard,
)
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.tools.delete_upload import DeleteUploadAlgorithm
from geoplateforme.toolbelt import PlgLogger


class UploadDetailsWidget(QWidget):
    select_stored_data = pyqtSignal(str)
    upload_deleted = pyqtSignal(str)

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

        self.vector_db_wizard = None

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

    def set_upload(self, upload: Upload) -> None:
        """
        Define displayed upload

        Args:
            upload: Upload
        """
        self._upload = upload
        self._set_upload_details(upload)

        # Remove all available action
        self.clear_layout(self.action_layout)

        status = upload.status

        # Data delete
        delete_action = QAction(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Supprimer.svg")),
            self.tr("Suppression"),
            self,
        )
        delete_action.triggered.connect(self.delete_upload)
        button = QToolButton(self)
        button.setDefaultAction(delete_action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.action_layout.addWidget(button)

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
            self.action_layout.addWidget(button)
        elif status == UploadStatus.OPEN:
            close_action = QAction(
                self.tr("Fermeture"),
                self,
            )
            close_action.triggered.connect(self.close_upload)
            button = QToolButton(self)
            button.setDefaultAction(close_action)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.action_layout.addWidget(button)

        # Add spacer to have button align left
        self.action_layout.addItem(
            QSpacerItem(
                40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
            )
        )

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

    def delete_upload(self) -> None:
        """Delete current upload"""
        reply = QMessageBox.question(
            self,
            self.tr("Suppression livraison"),
            self.tr("Êtes-vous sûr de vouloir supprimer la livraison ?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            params = {
                DeleteUploadAlgorithm.DATASTORE: self._upload.datastore_id,
                DeleteUploadAlgorithm.UPLOAD: self._upload._id,
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteUploadAlgorithm().name()}"
            )
            alg = QgsApplication.processingRegistry().algorithmById(algo_str)
            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()
            _, success = alg.run(parameters=params, context=context, feedback=feedback)
            if success:
                self.upload_deleted.emit(self._upload._id)
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Suppression livraison"),
                    self.tr("La livraison n'a pas pu être supprimée:\n {}").format(
                        feedback.textLog()
                    ),
                )

    def close_upload(self) -> None:
        """Close current upload"""
        reply = QMessageBox.question(
            self,
            self.tr("Fermeture livraison"),
            self.tr("Voulez vous fermer la livraison ?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                manager = UploadRequestManager()
                manager.close_upload(
                    datastore_id=self._upload.datastore_id, upload_id=self._upload._id
                )
            except UploadClosingException as exc:
                QMessageBox.critical(
                    self,
                    self.tr("Fermeture livraison"),
                    self.tr("La livraison n'a pas pu être fermée:\n {}").format(exc),
                )

    def _load_generation_report(self) -> None:
        """
        Load generation report for current upload
        """
        if self._upload:
            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            self.clear_layout(self.vlayout_execution)
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
