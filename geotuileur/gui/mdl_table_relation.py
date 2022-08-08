from qgis.PyQt.QtCore import QObject, Qt

from geotuileur.api.stored_data import (
    StoredData,
    StoredDataRequestManager,
    TableRelation,
)
from geotuileur.toolbelt import PlgLogger
from geotuileur.toolbelt.check_state_model import CheckStateModel


class TableRelationTreeModel(CheckStateModel):
    NAME_COL = 0
    TYPE_COL = 1

    def __init__(self, parent: QObject = None):
        """
        QStandardItemModel for table relation tree display

        Args:
            parent: QObject parent
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Attribute type")])
        self.check_state_enabled = True

    def set_stored_data(self, datastore: str, stored_data: str) -> None:
        """
        Refresh QStandardItemModel data with current stored data

        """
        self.removeRows(0, self.rowCount())

        manager = StoredDataRequestManager()
        try:
            stored_data = manager.get_stored_data(datastore, stored_data)
            self._insert_table_relations(stored_data.get_tables())
        except StoredDataRequestManager.ReadStoredDataException as exc:
            self.log(
                self.tr("Error while getting stored data informations: {0}").format(
                    exc
                ),
                log_level=2,
                push=False,
            )

    def set_stored_data_tables(self, stored_data: StoredData) -> None:
        """
        Refresh QStandardItemModel data with current stored data

        """
        self.removeRows(0, self.rowCount())
        self._insert_table_relations(stored_data.get_tables())

    def get_selected_table_attributes(self) -> {str: [str]}:
        """
        Get selected attributes for each stored data table

        Returns: dictionnary with selected attributes for each table

        """
        result = {}
        for row in range(0, self.rowCount()):
            table_index = self.index(row, self.NAME_COL)
            table = self.data(table_index)
            result[table] = []
            for table_attribute in range(0, self.rowCount(table_index)):
                attribute_index = self.index(row, self.NAME_COL, table_index)
                if (
                    not self.check_state_enabled
                    or self.data(attribute_index, Qt.CheckStateRole) == Qt.Checked
                ):
                    result[table].append(self.data(attribute_index))
        return result

    def _insert_table_relations(self, table_relation_list: [TableRelation]) -> None:
        """
        Insert table relation list

        Args:
            table_relation_list: table relation list
        """
        for table in table_relation_list:
            self._insert_table_relation(table)

    def _insert_table_relation(self, table_relation: TableRelation) -> None:
        """
        Insert a table relation

        Args:
            table_relation: TableRelation
        """
        row = self.rowCount()
        self.insertRow(row)
        table_index = self.index(row, self.NAME_COL)
        if self.check_state_enabled:
            self.setData(
                self.index(row, self.NAME_COL),
                Qt.Unchecked,
                Qt.CheckStateRole,
            )
        self.insertColumns(0, self.columnCount(), table_index)

        self.setData(table_index, table_relation.name)

        for attribute, val in table_relation.attributes.items():
            if attribute not in table_relation.primary_key and "geometry" not in val:
                row = self.rowCount(table_index)
                self.insertRow(row, table_index)
                self.setData(self.index(row, self.NAME_COL, table_index), attribute)
                if self.check_state_enabled:
                    self.setData(
                        self.index(row, self.NAME_COL, table_index),
                        Qt.Unchecked,
                        Qt.CheckStateRole,
                    )
                self.setData(self.index(row, self.TYPE_COL, table_index), val)
