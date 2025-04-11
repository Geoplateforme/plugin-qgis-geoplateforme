from typing import List

from qgis.PyQt.QtCore import QModelIndex, QObject, QSortFilterProxyModel, Qt

from geoplateforme.api.stored_data import StorageType, StoredDataStatus, StoredDataStep
from geoplateforme.gui.mdl_stored_data import StoredDataListModel


class StoredDataProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.filter_type = []
        self.visible_status = []
        self.invisible_status = []
        self.steps = []
        self.storage_types = []

    def set_filter_type(self, filter_type: List) -> None:
        """
        Define filter of expected stored data type

        Args:
            filter_type: expected stored data type
        """
        self.filter_type = filter_type

    def set_visible_steps(self, steps: [StoredDataStep]) -> None:
        """
        Define filter of visible steps for stored data

        Args:
            steps: List[StoredDataStep] visible step list
        """
        self.steps = steps

    def set_visible_storage_type(self, storage_types: [StorageType]) -> None:
        """
        Define filter of visible storage type for stored data

        Args:
            storage_types: List[StorageType] visible storage type list
        """
        self.storage_types = storage_types

    def set_visible_status(self, status: List[StoredDataStatus]) -> None:
        """
        Define filter of visible status for stored data

        Args:
            status: List[StoredDataStatus] visible status list
        """
        self.visible_status = status

    def set_invisible_status(self, status: List[StoredDataStatus]) -> None:
        """
        Define filter of inviseble status for stored data

        Args:
            status: List[StoredDataStatus] invisible status list
        """
        self.invisible_status = status

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Filter visible rows for stored data

        Args:
            source_row: (int) source row
            source_parent: (QModelIndex) source parent

        Returns: True if row is visible, False otherwise

        """
        result = True

        # Check stored_data type
        if len(self.filter_type):
            type_index = self.sourceModel().index(
                source_row, StoredDataListModel.TYPE_COL, source_parent
            )
            type_value = self.sourceModel().data(
                type_index, Qt.ItemDataRole.DisplayRole
            )

            result = type_value in self.filter_type

        # Check stored data status
        if (len(self.visible_status) or len(self.invisible_status)) and result:
            status_index = self.sourceModel().index(
                source_row, StoredDataListModel.STATUS_COL, source_parent
            )
            status_value = self.sourceModel().data(
                status_index, Qt.ItemDataRole.DisplayRole
            )
            if status_value:
                status = StoredDataStatus[status_value]
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
