from qgis.core import QgsApplication
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QObject, QSize, Qt, QVariant
from qgis.PyQt.QtGui import QIcon, QPixmap, QStandardItemModel

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.custom_exceptions import ReadStoredDataException
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataRequestManager,
    StoredDataStatus,
    StoredDataStep,
)
from geoplateforme.api.utils import as_datetime
from geoplateforme.toolbelt import PlgLogger


class StoredDataListModel(QStandardItemModel):
    NAME_COL = 0
    DATE_COL = 1
    ID_COL = 2
    TYPE_COL = 3
    STATUS_COL = 4
    ACTION_COL = 5
    DELETE_COL = 6
    REPORT_COL = 7
    OTHER_ACTIONS_COL = 8

    def __init__(self, parent: QObject = None):
        """
        QStandardItemModel for datastore list display

        Args:
            parent: QObject parent
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels(
            [
                self.tr("Name"),
                self.tr("Date"),
                self.tr("id"),
                self.tr("Type"),
                self.tr("Status"),
                self.tr("Action"),
                self.tr("Delete"),
                self.tr("Report"),
                self.tr("Other actions"),
            ]
        )

    def get_stored_data_row(self, stored_data_id: str) -> int:
        """
        Get stored data row from stored data id, returns -1 if stored data not available

        Args:
            stored_data_id: (str) stored data id

        Returns: (int) stored data id row, -1 if stored data not available

        """
        result = -1
        for row in range(0, self.rowCount()):
            if self.data(self.index(row, self.ID_COL)) == stored_data_id:
                result = row
                break
        return result

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole
    ) -> QVariant:
        """
        Override QStandardItemModel data() for :
        - decoration role for status icon

        Args:
            index: QModelIndex
            role: Qt role

        Returns: QVariant

        """
        result = super().data(index, role)
        if role == QtCore.Qt.DecorationRole:
            if index.column() == self.NAME_COL:
                type_ = self.data(
                    self.index(index.row(), self.TYPE_COL), QtCore.Qt.DisplayRole
                )
                status_value = self.data(
                    self.index(index.row(), self.STATUS_COL), QtCore.Qt.DisplayRole
                )
                status = StoredDataStatus[status_value]

                filename_suffix = ""
                if status == StoredDataStatus.UNSTABLE:
                    filename_suffix = "-unstable"
                elif status == StoredDataStatus.GENERATED:
                    filename_suffix = "-generated"

                filename = ""
                if status == StoredDataStatus.GENERATING:
                    filename = "generating.png"
                elif type_ == "VECTOR-DB":
                    filename = f"db{filename_suffix}.png"
                elif type_ == "ROK4-PYRAMID-VECTOR":
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
            elif index.column() == self.DELETE_COL:
                result = QIcon(QgsApplication.iconPath("mActionRemove.svg"))
            elif index.column() == self.REPORT_COL:
                result = QIcon(QgsApplication.iconPath("mIconReport.svg"))
        elif role == QtCore.Qt.DisplayRole and index.column() == self.ACTION_COL:
            stored_data = self.data(
                self.index(index.row(), self.NAME_COL), QtCore.Qt.UserRole
            )
            if stored_data:
                status = StoredDataStatus[stored_data.status]
                if status == StoredDataStatus.GENERATING:
                    result = self.tr("Progress")
                elif status == StoredDataStatus.GENERATED:
                    current_step = stored_data.get_current_step()
                    if current_step == StoredDataStep.TILE_GENERATION:
                        result = self.tr("Generate")
                    elif current_step == StoredDataStep.TILE_SAMPLE:
                        result = self.tr("View")
                    elif current_step == StoredDataStep.TILE_PUBLICATION:
                        result = self.tr("Publish")
                    elif current_step == StoredDataStep.TILE_UPDATE:
                        result = self.tr("Compare")
                    elif current_step == StoredDataStep.PUBLISHED:
                        result = self.tr("View")
                else:
                    result = self.tr("Report")

        return result

    def set_datastore(self, datastore: str) -> None:
        """
        Refresh QStandardItemModel data with current datastore stored data

        """
        self.removeRows(0, self.rowCount())

        manager = StoredDataRequestManager()
        try:
            stored_datas = manager.get_stored_data_list(datastore)
            for stored_data in stored_datas:
                self.insert_stored_data(stored_data)
        except ReadStoredDataException as exc:
            self.log(
                f"Error while getting stored data informations: {exc}",
                log_level=2,
                push=False,
            )

    def insert_stored_data(self, stored_data: StoredData) -> None:
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
        self.setData(self.index(row, self.ID_COL), stored_data.id)
        self.setData(self.index(row, self.TYPE_COL), stored_data.type)
        self.setData(self.index(row, self.STATUS_COL), stored_data.status)
        self.setData(self.index(row, self.OTHER_ACTIONS_COL), "...")
