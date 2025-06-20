from qgis.PyQt.QtCore import QModelIndex, QObject, Qt
from qgis.PyQt.QtGui import QStandardItemModel

from geoplateforme.api.catalogs import CatalogRequestManager
from geoplateforme.api.custom_exceptions import UnavailableUserException
from geoplateforme.api.user import Community, UserRequestsManager
from geoplateforme.toolbelt import PlgLogger


class CommunityListModel(QStandardItemModel):
    NAME_COL = 0

    def __init__(self, parent: QObject = None, checkable: bool = False):
        """QStandardItemModel for community list display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels(
            [
                self.tr("Nom"),
            ]
        )
        self._checkable = checkable

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Define flags for model

        :param index: model index
        :type index: QModelIndex
        :return: item flags
        :rtype: Qt.ItemFlags
        """
        # All item are enabled and selectable
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == self.NAME_COL and self._checkable:
            flags = flags | Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def refresh(self) -> None:
        """Refresh QStandardItemModel data with current user community"""
        self.removeRows(0, self.rowCount())

        try:
            manager = UserRequestsManager()
            user = manager.get_user()
            for community in user.get_community_list():
                self.insert_community(community)

            catalog_manager = CatalogRequestManager()
            for community in catalog_manager.get_community_list():
                self.insert_community(community)

        except UnavailableUserException as exc:
            self.log(
                f"Error while getting user informations: {exc}",
                log_level=2,
                push=False,
            )

    def insert_community(self, community: Community) -> None:
        """Insert community in model

        :param community: community to insert
        :type community: Community
        """
        row = self.rowCount()
        self.insertRow(row)

        self.setData(self.index(row, self.NAME_COL), community.name)
        if self._checkable:
            self.setData(
                self.index(row, self.NAME_COL),
                Qt.CheckState.Unchecked,
                Qt.ItemDataRole.CheckStateRole,
            )
        self.setData(
            self.index(row, self.NAME_COL), community, Qt.ItemDataRole.UserRole
        )

    def get_checked_community(self, checked: bool = True) -> list[Community]:
        """Return community with wanted checked status

        :param checked: wanted check status, defaults to True
        :type checked: bool, optional
        :return: list of community
        :rtype: list[Community]
        """
        result = []
        for row in range(self.rowCount()):
            row_checked = (
                self.data(
                    self.index(row, self.NAME_COL), Qt.ItemDataRole.CheckStateRole
                )
                == Qt.CheckState.Checked
            )
            if row_checked == checked:
                result.append(
                    self.data(self.index(row, self.NAME_COL), Qt.ItemDataRole.UserRole)
                )

        return result
