from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QStandardItemModel

from geoplateforme.api.custom_exceptions import UnavailableUserException
from geoplateforme.api.stored_data import StoredDataField, StoredDataRequestManager
from geoplateforme.toolbelt import PlgLogger


class DatasetListModel(QStandardItemModel):
    NAME_COL = 0

    def __init__(self, parent: QObject = None):
        """QStandardItemModel for dataset list display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels([self.tr("Name")])
        self.datastore_id = None

    def set_datastore_id(self, datastore_id: str) -> None:
        """Define current datastore id

        :param datastore_id: datastore id
        :type datastore_id: str
        """
        self.datastore_id = datastore_id

    def get_dataset_row(self, dataset_name: str) -> int:
        """Get dataset row from dataset name, returns -1 if dataset not available

        :param dataset_name: dataset name
        :type dataset_name: str

        :return: dataset name row, -1 if dataset not available
        :rtype: int
        """
        result = -1
        for row in range(0, self.rowCount()):
            if self.data(self.index(row, self.NAME_COL)) == dataset_name:
                result = row
                break
        return result

    def refresh(self, force: bool = False) -> None:
        """Refresh QStandardItemModel data with current user dataset

        :param force: force refresh
        :type force: bool
        """
        if force or self.rowCount() == 0:
            self.removeRows(0, self.rowCount())
            try:
                if self.datastore_id:
                    manager = StoredDataRequestManager()
                    stored_datas = manager.get_stored_data_list(
                        datastore_id=self.datastore_id,
                        with_fields=[StoredDataField.TAGS],
                    )

                    for stored_data in stored_datas:
                        # Here we call stored_data._tags because we already request TAGS
                        # (call stored_data.tags will generate unecessary requests on untag stored data)
                        for key, value in dict.items(stored_data._tags):
                            if (
                                key == "datasheet_name"
                                and self.get_dataset_row(value) == -1
                            ):
                                self.insertRow(self.rowCount())
                                row = self.rowCount() - 1
                                self.setData(self.index(row, self.NAME_COL), value)

            except UnavailableUserException as exc:
                self.log(
                    f"Error while getting user dataset: {exc}",
                    log_level=2,
                    push=False,
                )
