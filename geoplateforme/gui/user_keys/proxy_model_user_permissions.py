from datetime import datetime, timezone

from qgis.PyQt.QtCore import QModelIndex, QObject, QSortFilterProxyModel, Qt

from geoplateforme.gui.user_keys.mdl_user_permissions import UserPermissionListModel


class UserPermissionListProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Filter visible rows for stored data

        :param source_row: source row
        :type source_row: int
        :param source_parent: source parent
        :type source_parent: QModelIndex

        :return: True if row is visible, False otherwise
        :rtype: bool

        """
        result = True

        value_index = self.sourceModel().index(
            source_row, UserPermissionListModel.LICENCE_COL, source_parent
        )
        permission = self.sourceModel().data(value_index, Qt.ItemDataRole.UserRole)
        if permission and permission.end_date:
            result = permission.end_date > datetime.now(timezone.utc)

        return result
