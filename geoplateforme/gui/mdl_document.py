import json
from typing import Optional

from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QObject, Qt, QVariant
from qgis.PyQt.QtGui import QStandardItemModel

from geoplateforme.api.annexes import (
    AnnexeRequestManager,
)
from geoplateforme.api.custom_exceptions import ReadDocumentListException
from geoplateforme.toolbelt import PlgLogger


class DocumentListModel(QStandardItemModel):
    NAME_COL = 0
    DESCRIPTION_COL = 1
    TYPE_COL = 2
    URL_COL = 3

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
                self.tr("Description"),
                self.tr("type"),
                # self.tr("url"),
            ]
        )

    def set_datastore(
        self, datastore_id: str, dataset_name: Optional[str] = None
    ) -> None:
        """Refresh QStandardItemModel data with current datastore

        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str, optional
        """
        self.removeRows(0, self.rowCount())

        manager = AnnexeRequestManager()
        try:
            if dataset_name:
                labels = [f"datasheet_name={dataset_name}", "type=document-list"]
                annexes = manager.get_annexe_list(
                    datastore_id=datastore_id,
                    labels=labels,
                )
                if len(annexes) > 0:
                    annexe_id = annexes[0]._id
                    annexe_file = manager.get_annexe_file(
                        datastore_id=datastore_id, annexe_id=annexe_id
                    )
                    document_list = json.loads(annexe_file)
                    for document in document_list:
                        self.insert_document(document)
        except ReadDocumentListException as exc:
            self.log(
                f"Error while getting document informations: {exc}",
                log_level=2,
                push=False,
            )

    def data(
        self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
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
        if role == Qt.ItemDataRole.ToolTipRole:
            result = self.tr("Double click to open document in browser")
        return result

    def insert_document(self, document: dict) -> None:
        """Insert stored data in model

        :param stored_data: stored data to insert
        :type stored_data: StoredData
        """
        row = self.rowCount()
        self.insertRow(row)

        self.setData(self.index(row, self.NAME_COL), document, Qt.ItemDataRole.UserRole)
        self.setData(self.index(row, self.NAME_COL), document["name"])
        self.setData(self.index(row, self.DESCRIPTION_COL), document["description"])
        self.setData(self.index(row, self.TYPE_COL), document["type"])
        self.setData(self.index(row, self.URL_COL), document["url"])
