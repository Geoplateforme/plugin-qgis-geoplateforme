from typing import Optional

from qgis.PyQt.QtCore import QObject, Qt
from qgis.PyQt.QtGui import QStandardItemModel

from geoplateforme.api.custom_exceptions import ReadPermissionException
from geoplateforme.api.permissions import (
    PermissionAccountBeneficiary,
    PermissionCommunityBeneficiary,
    PermissionRequestManager,
)
from geoplateforme.toolbelt import PlgLogger


class PermissionListModel(QStandardItemModel):
    LICENCE_COL = 0
    END_DATE_COL = 1
    GRANTED_TO = 2
    SERVICES = 3

    def __init__(self, parent: QObject = None):
        """QStandardItemModel for user keys list display

        :param parent: parent
        :type parent: QObject
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels(
            [
                self.tr("Licence"),
                self.tr("Date d'expiration"),
                self.tr("Accordé à"),
                self.tr("Services"),
            ]
        )

    def refresh(self, datastore_id: str, offering_id: Optional[str] = None) -> None:
        """Refresh QStandardItemModel data with datastore permission filtered by offering if defined

        :param datastore_id: datastore id
        :type datastore_id: str
        :param offering_id: optional offering id
        :type offering_id: Optional[str]
        """
        self.removeRows(0, self.rowCount())
        try:
            manager = PermissionRequestManager()
            permissions = manager.get_permission_list(
                datastore_id=datastore_id, offering_id=offering_id
            )

            for permission in permissions:
                self.insertRow(self.rowCount())
                row = self.rowCount() - 1
                self.setData(self.index(row, self.LICENCE_COL), permission.licence)
                self.setData(
                    self.index(row, self.LICENCE_COL),
                    permission,
                    Qt.ItemDataRole.UserRole,
                )
                if permission.end_date:
                    self.setData(
                        self.index(row, self.END_DATE_COL), permission.end_date
                    )
                else:
                    self.setData(self.index(row, self.END_DATE_COL), self.tr("Aucune"))

                if permission.beneficiary:
                    if isinstance(permission.beneficiary, PermissionAccountBeneficiary):
                        granted_str = self.tr("L'utilisateur {} {}").format(
                            permission.beneficiary.first_name,
                            permission.beneficiary.last_name,
                        )
                    elif isinstance(
                        permission.beneficiary, PermissionCommunityBeneficiary
                    ):
                        granted_str = self.tr("La communauté {}").format(
                            permission.beneficiary.name
                        )
                    else:
                        granted_str = self.tr("Bénéficiaire inconnu")
                    self.setData(self.index(row, self.GRANTED_TO), granted_str)

                service_str = "\n".join(
                    [
                        f"{offering.layer_name} - {offering.type.value}"
                        for offering in permission.offerings
                    ]
                )
                self.setData(self.index(row, self.SERVICES), service_str)

        except ReadPermissionException as exc:
            self.log(
                f"Error while getting permissions: {exc}",
                log_level=2,
                push=False,
            )
