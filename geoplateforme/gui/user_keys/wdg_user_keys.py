# standard
import os

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QWidget
from qgis.utils import OverrideCursor

# plugin
from geoplateforme.gui.user_keys.dlg_user_key_creation import UserKeyCreationDialog
from geoplateforme.gui.user_keys.mdl_user_keys import UserKeysListModel
from geoplateforme.gui.user_keys.wdg_user_key import UserKeyWidget


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

        self.tbv_user_keys.pressed.connect(self._user_key_clicked)

        self.btn_add.setIcon(QIcon(":images/themes/default/locked.svg"))
        self.btn_add.clicked.connect(self._add_user_key)

        self.btn_refresh.clicked.connect(lambda: self.refresh(True))
        self.btn_refresh.setIcon(QIcon(":/images/themes/default/mActionRefresh.svg"))

        self.detail_dialog = None
        self.remove_detail_zone()

    def _user_key_clicked(self, index: QModelIndex) -> None:
        # Hide detail zone
        self.remove_detail_zone()

        # Get user key
        user_key = self.mdl_user_keys.data(
            self.mdl_user_keys.index(index.row(), UserKeysListModel.NAME_COL),
            Qt.ItemDataRole.UserRole,
        )
        if user_key:
            self.detail_dialog = UserKeyWidget(self)
            self.detail_dialog.set_user_key(user_key)
            self.detail_widget_layout.addWidget(self.detail_dialog)
            self.detail_dialog.user_key_deleted.connect(self._user_key_deleted)
            self.detail_dialog.user_key_updated.connect(self._user_key_updated)
            self.detail_zone.show()

    def _user_key_deleted(self, user_key_id: str) -> None:
        """Refresh after user key delete

        :param user_key_id: deleted user key id
        :type user_key_id: str
        """
        self.mdl_user_keys.refresh(force=True)
        self.remove_detail_zone()

    def _user_key_updated(self, user_key_id: str) -> None:
        """Refresh after user key update

        :param user_key_id: updated user key id
        :type user_key_id: str
        """
        self.mdl_user_keys.refresh(force=True)
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
