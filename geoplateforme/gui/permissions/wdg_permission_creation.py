# standard
import os
from typing import Optional

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QDateTime, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
    QWidget,
)

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.permissions import PermissionType
from geoplateforme.api.user import Community
from geoplateforme.gui.mdl_community import CommunityListModel
from geoplateforme.gui.mdl_offering import OfferingListModel
from geoplateforme.gui.proxy_model_offering import OfferingProxyModel

# plugin


class PermissionCreationWidget(QWidget):
    def __init__(self, parent: QWidget):
        """
        QWidget to create permission

        Args:
            parent:
        """
        super().__init__(parent)
        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_permission_creation.ui"), self
        )

        self.datastore_id = None

        # Model for offering
        self.mdl_offering = OfferingListModel(parent=self, checkable=True)
        self.proxy_mdl_offering = OfferingProxyModel(self)
        self.proxy_mdl_offering.setSourceModel(self.mdl_offering)
        self.proxy_mdl_offering.set_open_filter(open_filter=False)

        # Display only name and type in tableview
        self.tbv_offering.setModel(self.proxy_mdl_offering)
        self.tbv_offering.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_offering.setColumnHidden(OfferingListModel.ID_COL, True)
        self.tbv_offering.setColumnHidden(OfferingListModel.VISIBILITY_COL, True)
        self.tbv_offering.setColumnHidden(OfferingListModel.STATUS_COL, True)
        self.tbv_offering.setColumnHidden(OfferingListModel.OPEN_COL, True)
        self.tbv_offering.setColumnHidden(OfferingListModel.AVAILABLE_COL, True)
        self.tbv_offering.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tbv_offering.verticalHeader().setVisible(False)

        # Model for community
        self.mdl_community = CommunityListModel(parent=self, checkable=True)
        self.tbv_community.setModel(self.mdl_community)
        self.tbv_community.verticalHeader().setVisible(False)
        self.tbv_community.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Table widget for user
        self.tbw_user.setColumnCount(1)
        self.tbw_user.setHorizontalHeaderLabels([self.tr("Utilisateur")])
        self.tbw_user.verticalHeader().setVisible(False)
        self.tbw_user.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Update display page with radiobutton
        self.rbtn_community.toggled.connect(self._permission_type_updated)
        self.rbtn_user.toggled.connect(self._permission_type_updated)

        # Connection for user and community add
        self.btn_add_community.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))
        self.btn_add_user.clicked.connect(self._add_user)
        self.btn_add_user.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))
        self.btn_add_community.clicked.connect(self._add_community)

        # Connection for user and community delete
        self.btn_delete_user.clicked.connect(self._del_selected_user)
        self.btn_delete_user.setEnabled(False)
        self.btn_delete_user.setIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Supprimer.svg"))
        )
        self.btn_delete_community.clicked.connect(self._del_selected_community)
        self.btn_delete_community.setEnabled(False)
        self.btn_delete_community.setIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Supprimer.svg"))
        )

        # Connection for selection update
        self.tbw_user.itemSelectionChanged.connect(
            self._update_user_delete_button_state
        )
        self.tbv_community.selectionModel().selectionChanged.connect(
            self._update_community_delete_button_state
        )

        # No end date by default
        self.datetime_end_date.setNullRepresentation(self.tr("Aucune"))
        self.datetime_end_date.setDateTime(QDateTime())

        # Update add button if value are invalid
        self.btn_add_community.setEnabled(False)
        self.lne_community.textChanged.connect(self._update_add_community_button_state)
        self.btn_add_user.setEnabled(False)
        self.lne_user.textChanged.connect(self._update_add_user_button_state)

        self._added_community_id = []

    def _del_selected_user(self) -> None:
        """Remove selected user"""
        rows = [x.row() for x in self.tbw_user.selectedIndexes()]
        rows.sort(reverse=True)
        for row in rows:
            self.tbw_user.removeRow(row)

    def _update_user_delete_button_state(self) -> None:
        """Enable delete button if at least one row is selected for user table."""
        selected_rows = {item.row() for item in self.tbw_user.selectedItems()}
        self.btn_delete_user.setEnabled(bool(selected_rows))

    def _update_add_user_button_state(self) -> None:
        """Enable add button if user is valid"""
        self.btn_add_user.setEnabled(self.lne_user.valid())

    def _get_deletable_selected_community_row(self) -> list[int]:
        """Get list of selected community row that can be deleted

        :return: deletable selected community row
        :rtype: list[int]
        """
        selected_indexes = self.tbv_community.selectionModel().selectedIndexes()
        row_to_delete = []
        for index in selected_indexes:
            community = index.data(Qt.ItemDataRole.UserRole)
            if community and community._id in self._added_community_id:
                row_to_delete.append(index.row())
        return row_to_delete

    def _del_selected_community(self) -> None:
        """Remove selected community if they were added by user"""
        row_to_delete = self._get_deletable_selected_community_row()
        row_to_delete.sort(reverse=True)
        for row in row_to_delete:
            self.mdl_community.removeRow(row)

    def _update_community_delete_button_state(self):
        """Enable delete button if at least one selected community can be deleted."""
        row_to_delete = self._get_deletable_selected_community_row()
        self.btn_delete_community.setEnabled(bool(row_to_delete))

    def _update_add_community_button_state(self) -> None:
        """Enable add button if community is valid"""
        self.btn_add_community.setEnabled(self.lne_community.valid())

    def set_datastore_id(self, datastore_id: str) -> None:
        """Define datastore id

        :param datastore_id: datastore id
        :type datastore_id: str
        """
        self.datastore_id = datastore_id

        self.mdl_offering.set_datastore(datastore_id, open_filter=False)
        self.mdl_community.refresh()

    def _permission_type_updated(self) -> None:
        """Change displayed page when permission type is changed"""
        if self.rbtn_community.isChecked():
            self.stack_user_community.setCurrentWidget(self.community_page)
        else:
            self.stack_user_community.setCurrentWidget(self.user_page)

    def _add_community(self) -> None:
        """Add a community to tableview"""
        community_id = self.lne_community.text()
        community = Community(
            _id=community_id,
            public=True,
            name=community_id,
            technical_name=community_id,
            supervisor="",
        )
        self._added_community_id.append(community_id)
        self.mdl_community.insert_community(community)

    def _add_user(self) -> None:
        """Add user to tablewidget"""
        user_id = self.lne_user.text()
        row = self.tbw_user.rowCount()
        self.tbw_user.insertRow(row)
        self.tbw_user.setItem(row, 0, QTableWidgetItem(user_id))

    def get_permission_type(self) -> PermissionType:
        """Get permission type

        :return: permission type
        :rtype: PermissionType
        """
        if self.rbtn_community.isChecked():
            return PermissionType.COMMUNITY
        return PermissionType.ACCOUNT

    def get_licence(self) -> str:
        """Get licence

        :return: licence
        :rtype: str
        """
        return self.lne_licence.text()

    def get_end_date(self) -> Optional[QDateTime]:
        """Get end date if defined

        :return: end date, None if not defined
        :rtype: Optional[QDateTime]
        """
        end_date = self.datetime_end_date.dateTime()
        if not end_date.isNull():
            return end_date
        return None

    def get_offering_ids(self) -> list[str]:
        """Get list of checked offering ids

        :return: checked offering ids
        :rtype: list[str]
        """
        return [
            offering._id
            for offering in self.mdl_offering.get_checked_offering(checked=True)
        ]

    def get_user_ids(self) -> list[str]:
        """Get list of user ids

        :return: user ids
        :rtype: list[str]
        """
        return [
            self.tbw_user.item(row, 0).text() for row in range(self.tbw_user.rowCount())
        ]

    def get_community_ids(self) -> list[str]:
        """Get list of checked community ids

        :return: check community ids
        :rtype: list[str]
        """
        return [
            community._id
            for community in self.mdl_community.get_checked_community(checked=True)
        ]

    def get_only_oauth(self) -> bool:
        """Get only oauth option

        :return: True if only oauth option is checked, False otherwise
        :rtype: bool
        """
        return self.ckb_only_oauth.isChecked()
