from typing import List

from qgis.PyQt.QtCore import QModelIndex, QObject, QSortFilterProxyModel, Qt

from geoplateforme.api.stored_data import (
    StorageType,
    StoredDataStatus,
    StoredDataStep,
    StoredDataType,
)
from geoplateforme.gui.mdl_stored_data import StoredDataListModel


class StoredDataProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.filter_type = []
        self.visible_status = []
        self.invisible_status = []
        self.steps = []
        self.storage_types = []

    def set_filter_type(self, filter_type: List[StoredDataType]) -> None:
        """Define filter of expected stored data type

        :param filter_type: expected stored data type
        :type filter_type: List[StoredDataType]
        """
        self.filter_type = filter_type

    def set_visible_steps(self, steps: List[StoredDataStep]) -> None:
        """Define filter of visible steps for stored data

        :param steps: visible step list
        :type steps: List[StoredDataStep]
        """
        self.steps = steps

    def set_visible_storage_type(self, storage_types: List[StorageType]) -> None:
        """Define filter of visible storage type for stored data

        :param storage_types: visible storage type list
        :type storage_types: List[StorageType]
        """
        self.storage_types = storage_types

    def set_visible_status(self, status: List[StoredDataStatus]) -> None:
        """Define filter of visible status for stored data

        :param status: visible status list
        :type status: List[StoredDataStatus]
        """
        self.visible_status = status

    def set_invisible_status(self, status: List[StoredDataStatus]) -> None:
        """Define filter of inviseble status for stored data

        :param status: invisible status list
        :type status: List[StoredDataStatus]
        """
        self.invisible_status = status

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

        # Check stored_data type
        if len(self.filter_type):
            type_index = self.sourceModel().index(
                source_row, StoredDataListModel.NAME_COL, source_parent
            )
            stored_data = self.sourceModel().data(type_index, Qt.ItemDataRole.UserRole)
            if stored_data:
                result = stored_data.type in self.filter_type

        # Check stored data status
        if (len(self.visible_status) or len(self.invisible_status)) and result:
            status_index = self.sourceModel().index(
                source_row, StoredDataListModel.STATUS_COL, source_parent
            )
            status_value = self.sourceModel().data(
                status_index, Qt.ItemDataRole.DisplayRole
            )
            if status_value:
                status = status_value
                if len(self.invisible_status):
                    result &= status not in self.invisible_status
                if len(self.visible_status):
                    result &= status in self.visible_status

        # Check stored data step
        if len(self.steps) and result:
            name_index = self.sourceModel().index(
                source_row, StoredDataListModel.NAME_COL, source_parent
            )
            stored_data = self.sourceModel().data(name_index, Qt.ItemDataRole.UserRole)
            if stored_data:
                result = stored_data.get_current_step() in self.steps

        # Check stored data storage types
        if len(self.storage_types) and result:
            name_index = self.sourceModel().index(
                source_row, StoredDataListModel.NAME_COL, source_parent
            )
            stored_data = self.sourceModel().data(name_index, Qt.ItemDataRole.UserRole)
            if stored_data:
                result = stored_data.get_storage_type() in self.storage_types

        return result
