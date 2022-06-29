from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QStandardItemModel

from vectiler.api.user import UserRequestsManager
from vectiler.toolbelt import PlgLogger


class DatastoreListModel(QStandardItemModel):
    NAME_COL = 0
    ID_COL = 1

    def __init__(self, parent: QObject = None):
        """
        QStandardItemModel for datastore list display

        Args:
            parent: QObject parent
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels([self.tr("Name"), self.tr("id")])
        self.refresh()

    def refresh(self) -> None:
        """
        Refresh QStandardItemModel data with current user datastore

        """
        self.removeRows(0, self.rowCount())

        try:
            manager = UserRequestsManager()
            user = manager.get_user()

            for datastore in user.get_datastore_list():
                self.insertRow(self.rowCount())
                row = self.rowCount() - 1

                self.setData(self.index(row, self.NAME_COL), datastore.name)
                self.setData(self.index(row, self.ID_COL), datastore.id)

        except UserRequestsManager.UnavailableUserException as exc:
            self.log(
                f"Error while getting user datastore: {exc}",
                log_level=2,
                push=False,
            )
