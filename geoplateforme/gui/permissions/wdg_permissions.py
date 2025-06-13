# standard
import os
from typing import Optional

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QAbstractItemView, QWidget

from geoplateforme.gui.permissions.mdl_permissions import PermissionListModel

# plugin


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

        self.detail_dialog = None
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
        self.mdl_permissions.refresh(datastore_id=datastore_id, offering_id=offering_id)
