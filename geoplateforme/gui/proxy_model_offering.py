from typing import Optional

from qgis.PyQt.QtCore import QModelIndex, QObject, QSortFilterProxyModel, Qt

from geoplateforme.gui.mdl_offering import OfferingListModel


class OfferingProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.open_filter = None

    def set_open_filter(self, open_filter: Optional[bool]) -> None:
        """Define filter for offering open status

        :param open_filter: expected stored data type
        :type open_filter: Optional[bool]
        """
        self.open_filter = open_filter

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

        # Check offering open
        if self.open_filter is not None:
            value_index = self.sourceModel().index(
                source_row, OfferingListModel.NAME_COL, source_parent
            )
            offering = self.sourceModel().data(value_index, Qt.ItemDataRole.UserRole)
            if offering:
                result = offering.open == self.open_filter

        return result
