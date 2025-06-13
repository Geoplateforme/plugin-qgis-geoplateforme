from typing import Optional

from qgis.PyQt.QtCore import QModelIndex, QObject, Qt
from qgis.PyQt.QtGui import QStandardItemModel

from geoplateforme.api.configuration import Configuration, ConfigurationRequestManager
from geoplateforme.api.custom_exceptions import (
    ReadConfigurationException,
    ReadOfferingException,
)
from geoplateforme.api.offerings import Offering, OfferingField, OfferingsRequestManager
from geoplateforme.toolbelt import PlgLogger


class OfferingListModel(QStandardItemModel):
    NAME_COL = 0
    ID_COL = 1
    TYPE_COL = 2
    VISIBILITY_COL = 3
    STATUS_COL = 4
    OPEN_COL = 5
    AVAILABLE_COL = 6

    def __init__(self, parent: QObject = None, checkable: bool = False):
        """QStandardItemModel for offering list display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels(
            [
                self.tr("Nom"),
                self.tr("ID"),
                self.tr("Type"),
                self.tr("Visibilité"),
                self.tr("Status"),
                self.tr("Ouvert"),
                self.tr("Disponibilité"),
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

        manager = ConfigurationRequestManager()
        try:
            if dataset_name:
                tags = {"datasheet_name": dataset_name}
                configurations = manager.get_configuration_list(
                    datastore_id=datastore_id,
                    tags=tags,
                )
            else:
                configurations = manager.get_configuration_list(
                    datastore_id=datastore_id,
                )
            for config in configurations:
                self.insert_configuration(config)
        except ReadConfigurationException as exc:
            self.log(
                f"Error while getting configuration informations: {exc}",
                log_level=2,
                push=False,
            )
        except ReadOfferingException as exc:
            self.log(
                f"Error while getting offering informations: {exc}",
                log_level=2,
                push=False,
            )

    def insert_configuration(self, config: Configuration) -> None:
        """Insert stored data in model

        :param stored_data: stored data to insert
        :type stored_data: StoredData
        """

        manager = OfferingsRequestManager()
        offering_list = manager.get_offering_list(
            datastore_id=config.datastore_id,
            with_fields=[
                OfferingField.LAYER_NAME,
                OfferingField.TYPE,
                OfferingField.OPEN,
                OfferingField.STATUS,
                OfferingField.AVAILABLE,
            ],
            configuration_id=config._id,
        )

        for offering in offering_list:
            self.insert_offering(offering)

    def insert_offering(self, offering: Offering) -> None:
        """Insert stored data in model

        :param stored_data: stored data to insert
        :type stored_data: StoredData
        """

        row = self.rowCount()
        self.insertRow(row)

        self.setData(self.index(row, self.NAME_COL), offering.layer_name)
        if self._checkable:
            self.setData(
                self.index(row, self.NAME_COL),
                Qt.CheckState.Unchecked,
                Qt.ItemDataRole.CheckStateRole,
            )

        self.setData(self.index(row, self.NAME_COL), offering, Qt.ItemDataRole.UserRole)
        self.setData(self.index(row, self.ID_COL), offering._id)
        self.setData(self.index(row, self.TYPE_COL), offering.type.value)
        # TODO : how to get visibility (PRIVATE / PUBLIC)
        # self.setData(self.index(row, self.VISIBILITY_COL), offering.type)
        self.setData(self.index(row, self.STATUS_COL), offering.status.value)
        self.setData(self.index(row, self.OPEN_COL), offering.open)
        self.setData(self.index(row, self.AVAILABLE_COL), offering.available)

    def get_checked_offering(self, checked: bool = True) -> list[Offering]:
        """Return offering with wanted checked status

        :param checked: wanted check status, defaults to True
        :type checked: bool, optional
        :return: list of offering
        :rtype: list[Offering]
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

    def get_offering_row(self, offering_id: str) -> int:
        """Get offering row for an id; returns -1 if offering is not available

        :param offering_id: offering id
        :type offering_id: str
        :return: offering id row, -1 if offering not available
        :rtype: int
        """
        result = -1
        for row in range(0, self.rowCount()):
            offering = self.data(
                self.index(row, self.NAME_COL), Qt.ItemDataRole.UserRole
            )
            if offering._id == offering_id:
                result = row
                break
        return result
