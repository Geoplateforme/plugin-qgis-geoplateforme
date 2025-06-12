from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QStandardItemModel

from geoplateforme.api.custom_exceptions import ReadUserKeyException
from geoplateforme.api.user_key import UserKeyRequestManager
from geoplateforme.toolbelt import PlgLogger


class UserKeysListModel(QStandardItemModel):
    NAME_COL = 0
    TYPE_COL = 1

    def __init__(self, parent: QObject = None):
        """QStandardItemModel for user keys list display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Type")])

    def refresh(self, force: bool = False) -> None:
        """Refresh QStandardItemModel data with current user keys

        :param force: force refresh
        :type force: bool
        """
        if force or self.rowCount() == 0:
            self.removeRows(0, self.rowCount())
            try:
                manager = UserKeyRequestManager()
                user_keys = manager.get_user_key_list()

                for user_key in user_keys:
                    self.insertRow(self.rowCount())
                    row = self.rowCount() - 1
                    self.setData(self.index(row, self.NAME_COL), user_key.name)
                    self.setData(self.index(row, self.TYPE_COL), user_key._type.value)

            except ReadUserKeyException as exc:
                self.log(
                    f"Error while getting user keys: {exc}",
                    log_level=2,
                    push=False,
                )
