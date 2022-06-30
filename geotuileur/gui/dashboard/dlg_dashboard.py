import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QWidget


class DashboardDialog(QDialog):
    def __init__(self, parent: QWidget):
        """
        QDialog to display dashboard

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "dlg_dashboard.ui"),
            self,
        )

    def refresh(self) -> None:
        """
        Force refresh of dashboad

        """
        self.wdg_dashboard.refresh()
