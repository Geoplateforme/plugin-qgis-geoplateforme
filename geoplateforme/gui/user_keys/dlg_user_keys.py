#! python3  # noqa: E265

"""
Dialog hosting user information (when logged in).
"""

# standard
import os

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QWidget


class UserKeysDialog(QDialog):
    def __init__(self, parent: QWidget):
        """
        Dialog to display current user information and disconnection button

        Args:
            parent: parent QObject

        Args:
            parent:
        """
        super().__init__(parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), "dlg_user_keys.ui"), self)
        self.setWindowTitle(self.tr("Clés d'accès"))

    def refresh(self, force: bool = False) -> None:
        """
        Refresh displayed user keys

        :param force: force refresh
        :type force: bool
        """
        self.wdg_user_keys.refresh(force=force)
