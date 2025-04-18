from typing import Optional

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QObject, QSize, Qt, QVariant
from qgis.PyQt.QtGui import QPixmap, QStandardItemModel

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.custom_exceptions import ReadStoredDataException
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataField,
    StoredDataRequestManager,
    StoredDataStatus,
    StoredDataType,
)
from geoplateforme.api.utils import as_datetime
from geoplateforme.toolbelt import PlgLogger


class StoredDataListModel(QStandardItemModel):
    NAME_COL = 0
    DATE_COL = 1
    STATUS_COL = 2

    def __init__(self, parent: QObject = None):
        """QStandardItemModel for stored data list display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels(
            [
                self.tr("Name"),
                self.tr("Date"),
                self.tr("Status"),
            ]
        )

    def get_stored_data_row(self, stored_data_id: str) -> int:
        """Get stored data row from stored data id, returns -1 if stored data not available

        :param stored_data_id: stored data id
        :type stored_data_id: str

        :return: stored data id row, -1 if stored data not available
        :rtype: int
        """
        result = -1
        for row in range(0, self.rowCount()):
            if (
                self.data(self.index(row, self.NAME_COL), Qt.ItemDataRole.UserRole).id
                == stored_data_id
            ):
                result = row
                break
        return result

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole
    ) -> QVariant:
        """Override QStandardItemModel data() for decoration role for status icon

        Args:
        :param index: index
        :type index: QModelIndex
        :param role: Qt role
        :type role: int

        :return: data at index with role
        :rtype: QVariant
        """
        result = super().data(index, role)
        if role == QtCore.Qt.DecorationRole:
            if index.column() == self.NAME_COL:
                stored_data = self.data(
                    self.index(index.row(), self.NAME_COL), Qt.ItemDataRole.UserRole
                )
                type_ = stored_data.type

                status_value = self.data(
                    self.index(index.row(), self.STATUS_COL), QtCore.Qt.DisplayRole
                )
                status = status_value

                filename_suffix = ""
                if status == StoredDataStatus.UNSTABLE:
                    filename_suffix = "-unstable"
                elif status == StoredDataStatus.GENERATED:
                    filename_suffix = "-generated"

                filename = ""
                if status == StoredDataStatus.GENERATING:
                    filename = "generating.png"
                elif type_ == StoredDataType("VECTOR-DB"):
                    filename = f"db{filename_suffix}.png"
                elif type_ == StoredDataType("ROK4-PYRAMID-VECTOR"):
                    filename = f"tiles{filename_suffix}.png"

                if filename:
                    filepath = str(
                        DIR_PLUGIN_ROOT
                        / "resources"
                        / "images"
                        / "dashboard"
                        / filename
                    )
                    result = QPixmap(filepath).scaled(
                        QSize(32, 32),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

        return result

    def set_datastore(
        self, datastore_id: str, dataset_name: Optional[str] = None
    ) -> None:
        """Refresh QStandardItemModel data with current datastore stored data

        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str, optional
        """
        self.removeRows(0, self.rowCount())

        manager = StoredDataRequestManager()
        try:
            if dataset_name:
                tags = {"datasheet_name": dataset_name}
                stored_datas = manager.get_stored_data_list(
                    datastore_id=datastore_id,
                    with_fields=[
                        StoredDataField.NAME,
                        StoredDataField.LASTEVENT,
                        StoredDataField.STATUS,
                        StoredDataField.TYPE,
                    ],
                    tags=tags,
                )
            else:
                stored_datas = manager.get_stored_data_list(
                    datastore_id=datastore_id,
                    with_fields=[
                        StoredDataField.NAME,
                        StoredDataField.LASTEVENT,
                        StoredDataField.STATUS,
                        StoredDataField.TYPE,
                    ],
                )
            for stored_data in stored_datas:
                self.insert_stored_data(stored_data)
        except ReadStoredDataException as exc:
            self.log(
                f"Error while getting stored data informations: {exc}",
                log_level=2,
                push=False,
            )

    def insert_stored_data(self, stored_data: StoredData) -> None:
        """Insert stored data in model

        :param stored_data: stored data to insert
        :type stored_data: StoredData
        """
        row = self.rowCount()
        self.insertRow(row)

        self.setData(self.index(row, self.NAME_COL), stored_data.name)
        self.setData(
            self.index(row, self.NAME_COL), stored_data, Qt.ItemDataRole.UserRole
        )
        self.setData(
            self.index(row, self.DATE_COL),
            as_datetime(stored_data.get_last_event_date()),
        )
        self.setData(self.index(row, self.STATUS_COL), stored_data.status.value)
