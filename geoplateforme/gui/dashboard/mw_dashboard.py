import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QMainWindow, QWidget


class DashboardWindow(QMainWindow):
    def __init__(self, parent: QWidget):
        """
        QDialog to display dashboard

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "mw_dashboard.ui"),
            self,
        )
        self.setWindowTitle(self.tr("Dashboard"))

    def refresh(self) -> None:
        """
        Force refresh of dashboad

        """
        self.wdg_dashboard.refresh()
