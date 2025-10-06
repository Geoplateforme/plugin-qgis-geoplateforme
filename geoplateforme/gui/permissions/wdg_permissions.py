# standard
import os
from typing import Optional

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QItemSelection, QModelIndex, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QHeaderView, QWidget
from qgis.utils import OverrideCursor

# plugin
from geoplateforme.gui.permissions.dlg_permission_creation import (
    PermissionCreationDialog,
)
from geoplateforme.gui.permissions.mdl_permissions import PermissionListModel
from geoplateforme.gui.permissions.wdg_permission import PermissionWidget


class PermissionsWidget(QWidget):
    def __init__(self, parent: QWidget):
        """
        QWidget to display permissions

        Args:
            parent:
        """
        super().__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), "wdg_permissions.ui"), self)

        self.mdl_permissions = PermissionListModel(self)
        self.tbv_permissions.setModel(self.mdl_permissions)
        self.tbv_permissions.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tbv_permissions.verticalHeader().setVisible(False)
        self.tbv_permissions.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tbv_permissions.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tbv_permissions.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tbv_permissions.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tbv_permissions.selectionModel().selectionChanged.connect(
            self._permission_selection_changed
        )

        self.detail_dialog = None
        self.remove_detail_zone()

        self.datastore_id = None
        self.offering_id = None

        self.btn_add_permission.setEnabled(False)
        self.btn_add_permission.setIcon(QIcon(":images/themes/default/locked.svg"))
        self.btn_add_permission.clicked.connect(self._add_permission)

    def _permission_selection_changed(self, selection: QItemSelection) -> None:
        """Display permission details when selection changed

        :param selection: selected item
        :type selection: QItemSelection
        """
        if len(selection.indexes()) > 0:
            index = selection.indexes()[0]
            self._permission_clicked(index)

    def _permission_clicked(self, index: QModelIndex) -> None:
        # Hide detail zone
        self.remove_detail_zone()

        # Get permission
        permission = self.mdl_permissions.data(
            self.mdl_permissions.index(index.row(), PermissionListModel.LICENCE_COL),
            Qt.ItemDataRole.UserRole,
        )
        if permission:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                self.detail_dialog = PermissionWidget(self)
                self.detail_dialog.set_permission(permission)
            self.detail_widget_layout.addWidget(self.detail_dialog)
            self.detail_dialog.permission_deleted.connect(self._permission_deleted)
            self.detail_dialog.permission_updated.connect(self._permission_updated)
            self.detail_zone.show()

    def _permission_deleted(self, permission_id: str) -> None:
        """Refresh after permission delete

        :param permission_id: deleted user key id
        :type permission_id: str
        """
        self.mdl_permissions.refresh(self.datastore_id)
        self.remove_detail_zone()

    def _permission_updated(self, permission_id: str) -> None:
        """Refresh after user key update

        :param permission_id: updated permission id
        :type permission_id: str
        """
        self.refresh(self.datastore_id, self.offering_id)
        self.remove_detail_zone()

    def remove_detail_zone(self) -> None:
        """Hide detail zone and remove attached widgets"""
        # Hide detail zone
        self.detail_zone.hide()
        if self.detail_dialog:
            self.detail_widget_layout.removeWidget(self.detail_dialog)
            self.detail_dialog = None

    def refresh(self, datastore_id: str, offering_id: Optional[str] = None) -> None:
        """Refresh displayed permission

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering_id: optional offering id
        :type offering_id: Optional[str]
        """
        self.datastore_id = datastore_id
        self.offering_id = offering_id

        self.mdl_permissions.refresh(datastore_id=datastore_id, offering_id=offering_id)
        self.btn_add_permission.setEnabled(self.datastore_id is not None)

    def _add_permission(self) -> None:
        """Display permission creation dialog and refresh display model if permission created"""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            dialog = PermissionCreationDialog(
                datastore_id=self.datastore_id, parent=self
            )
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.refresh(self.datastore_id, self.offering_id)
