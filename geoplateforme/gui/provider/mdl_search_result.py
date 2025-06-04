import json
from typing import Optional

# PyQGIS
from qgis.PyQt.QtCore import QByteArray, QModelIndex, QObject, Qt, QUrl
from qgis.PyQt.QtGui import QStandardItemModel

# plugin
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


class SearchResultModel(QStandardItemModel):
    TITLE_COL = 0
    PRODUCER_COL = 1
    THEME_COL = 2
    TYPE_COL = 3

    authorized_type = ["WMS", "TMS", "WMTS", "WFS"]

    def __init__(self, parent: QObject = None):
        """QStandardItemModel for search result display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.plg_settings = PlgOptionsManager.get_plg_settings()
        self.setHorizontalHeaderLabels(
            [
                self.tr("Title"),
                self.tr("Producer"),
                self.tr("Theme"),
                self.tr("Type"),
            ]
        )

    def clear(self):
        """Remove all results"""
        self.removeRows(0, self.rowCount())

    def get_result(self, index: QModelIndex) -> Optional[dict]:
        """Get result from index, returns -1 if result not available

        :param index: index
        :type index: int

        :return: result at index, None if result not available
        :rtype: int
        """
        result = None
        if index.isValid():
            result = self.data(
                self.index(index.row(), self.TITLE_COL), Qt.ItemDataRole.UserRole
            )
        return result

    def simple_search_text(self, text: str) -> None:
        """Refresh QStandardItemModel data with result on text search

        :param text: seach text
        :type text: str
        """
        self.removeRows(0, self.rowCount())
        request_manager = NetworkRequestsManager()
        # plg_settings = PlgOptionsManager.get_plg_settings()

        try:
            reply = request_manager.get_url(
                url=QUrl(
                    f"{self.plg_settings.base_url_api_search}/indexes/geoplateforme/suggest?size=50&text={text}"
                ),
            )
        except ConnectionError as err:
            self.log(
                f"Error while searching layers: {err}",
                log_level=2,
                push=False,
            )

        search_results = json.loads(reply.data())
        for result in search_results:
            if result["source"]["type"] in self.authorized_type:
                self.insert_result(result["source"])

    def advanced_search_text(self, search_dict: str) -> None:
        """Refresh QStandardItemModel data with result on text search

        :param search_dict: search dict
        :type search_dict: dict
        """
        self.removeRows(0, self.rowCount())
        request_manager = NetworkRequestsManager()
        # plg_settings = PlgOptionsManager.get_plg_settings()

        try:
            data = QByteArray()
            data_map = search_dict
            data.append(json.dumps(data_map))
            reply = request_manager.post_url(
                url=QUrl(
                    f"{self.plg_settings.base_url_api_search}/indexes/geoplateforme?page=1&size=50"
                ),
                data=data,
                headers={b"Content-Type": bytes("application/json", "utf8")},
            )
        except ConnectionError as err:
            self.log(
                f"Error while searching layers: {err}",
                log_level=2,
                push=False,
            )

        search_results = json.loads(reply.data())
        for document in search_results["documents"]:
            if document["type"] in self.authorized_type:
                self.insert_result(document)

    def insert_result(self, result: dict) -> None:
        """Insert result in model

        :param result: result to insert
        :type result: dict
        """
        row = self.rowCount()
        self.insertRow(row)

        self.setData(self.index(row, self.TITLE_COL), result["title"])
        self.setData(self.index(row, self.TITLE_COL), result, Qt.ItemDataRole.UserRole)
        if "producers" in result:
            self.setData(
                self.index(row, self.PRODUCER_COL), ", ".join(result["producers"])
            )
        else:
            self.setData(self.index(row, self.PRODUCER_COL), "")
        if "theme" in result:
            self.setData(self.index(row, self.THEME_COL), result["theme"])
        else:
            self.setData(self.index(row, self.THEME_COL), "")
        self.setData(self.index(row, self.TYPE_COL), result["type"])
