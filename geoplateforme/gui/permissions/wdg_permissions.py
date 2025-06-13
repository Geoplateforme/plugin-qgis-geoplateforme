# standard
import os
from typing import Optional

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QWidget
from qgis.utils import OverrideCursor

# plugin
from geoplateforme.gui.permissions.dlg_permission_creation import (
    PermissionCreationDialog,
)
from geoplateforme.gui.permissions.mdl_permissions import PermissionListModel


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

        self.detail_dialog = None
        self.remove_detail_zone()

        self.datastore_id = None
        self.offering_id = None

        self.btn_add_permission.setEnabled(False)
        self.btn_add_permission.setIcon(QIcon(":images/themes/default/locked.svg"))
        self.btn_add_permission.clicked.connect(self._add_permission)

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
        if result == QDialog.Accepted:
            self.refresh(self.datastore_id, self.offering_id)
