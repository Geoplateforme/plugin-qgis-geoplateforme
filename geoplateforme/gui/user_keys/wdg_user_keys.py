# standard
import os

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QWidget
from qgis.utils import OverrideCursor

# plugin
from geoplateforme.gui.user_keys.dlg_user_key_creation import UserKeyCreationDialog
from geoplateforme.gui.user_keys.mdl_user_keys import UserKeysListModel


class UserKeysWidget(QWidget):
    def __init__(self, parent: QWidget):
        """
        QWidget to display user keys

        Args:
            parent:
        """
        super().__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), "wdg_user_keys.ui"), self)

        self.mdl_user_keys = UserKeysListModel(self)
        self.mdl_user_keys.refresh()
        self.tbv_user_keys.setModel(self.mdl_user_keys)
        self.tbv_user_keys.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.btn_add.setIcon(QIcon(":images/themes/default/locked.svg"))
        self.btn_add.clicked.connect(self._add_user_key)

        self.detail_dialog = None
        self.remove_detail_zone()

    def _add_user_key(self) -> None:
        """Display user key creation dialog and refresh display model if permission created"""
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            dialog = UserKeyCreationDialog(parent=self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.refresh(force=True)

    def remove_detail_zone(self) -> None:
        """Hide detail zone and remove attached widgets"""
        # Hide detail zone
        self.detail_zone.hide()
        if self.detail_dialog:
            self.detail_widget_layout.removeWidget(self.detail_dialog)
            self.detail_dialog = None

    def refresh(self, force: bool = False) -> None:
        """
        Refresh displayed user keys

        :param force: force refresh
        :type force: bool
        """
        self.mdl_user_keys.refresh(force=force)
