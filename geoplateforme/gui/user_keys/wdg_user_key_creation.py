# standard
import os
from typing import Any, Tuple

from qgis.core import QgsApplication

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QAbstractItemView, QHeaderView, QMessageBox, QWidget

# plugin
from geoplateforme.api.offerings import Offering
from geoplateforme.api.permissions import Permission
from geoplateforme.api.user_key import UserKey
from geoplateforme.gui.user_keys.mdl_user_permissions import UserPermissionListModel
from geoplateforme.gui.user_keys.proxy_model_user_permissions import (
    UserPermissionListProxyModel,
)
from geoplateforme.processing.provider import GeoplateformeProvider
from geoplateforme.processing.user_key.create_basic_key import CreateBasicKeyAlgorithm
from geoplateforme.processing.user_key.create_hash_key import CreateHashKeyAlgorithm
from geoplateforme.processing.user_key.create_oauth_key import CreateOAuthKeyAlgorithm


class UserKeyCreationWidget(QWidget):
    def __init__(self, parent: QWidget):
        """
        QWidget to create user key

        Args:
            parent:
        """
        super().__init__(parent)
        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_user_key_creation.ui"), self
        )

        # Model for permission
        self.mdl_user_permission = UserPermissionListModel(parent=self, checkable=True)
        self.mdl_user_permission.refresh()

        self.proxy_mdl_user_permission = UserPermissionListProxyModel(self)
        self.proxy_mdl_user_permission.setSourceModel(self.mdl_user_permission)

        self.tbv_permissions.setModel(self.proxy_mdl_user_permission)
        self.tbv_permissions.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tbv_permissions.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tbv_permissions.verticalHeader().setVisible(False)

        # Update display page with radiobutton
        self.rbtn_basic.toggled.connect(self._key_type_updated)
        self.rbtn_hash.toggled.connect(self._key_type_updated)
        self.rbtn_oauth.toggled.connect(self._key_type_updated)

    def _key_type_updated(self) -> None:
        """Change displayed page when key type is changed"""
        if self.rbtn_basic.isChecked():
            self.stack_key.setCurrentWidget(self.page_basic)
        elif self.rbtn_hash.isChecked():
            self.stack_key.setCurrentWidget(self.page_hash)
        else:
            self.stack_key.setCurrentWidget(self.page_oauth)

    def get_creation_parameters(self) -> dict:
        """Get algorithm parameters for user key creation

        :return: user key creation algorithm parameters
        :rtype: dict
        """
        whitelist = self.wdg_user_key_ip_filter.get_whitelist()
        whitelist_str = ",".join(whitelist) if whitelist else ""
        blacklist = self.wdg_user_key_ip_filter.get_blacklist()
        blacklist_str = ",".join(blacklist) if blacklist else ""

        if self.rbtn_basic.isChecked():
            return {
                CreateBasicKeyAlgorithm.NAME: self.lne_name.text(),
                CreateBasicKeyAlgorithm.WHITELIST: whitelist_str,
                CreateBasicKeyAlgorithm.BLACKLIST: blacklist_str,
                CreateBasicKeyAlgorithm.USER_AGENT: self.lne_user_agent.text(),
                CreateBasicKeyAlgorithm.REFERER: self.lne_referer.text(),
                CreateBasicKeyAlgorithm.LOGIN: self.lne_login.text(),
                CreateBasicKeyAlgorithm.PASSWORD: self.lne_password.text(),
            }
        elif self.rbtn_hash.isChecked():
            return {
                CreateHashKeyAlgorithm.NAME: self.lne_name.text(),
                CreateHashKeyAlgorithm.WHITELIST: whitelist_str,
                CreateHashKeyAlgorithm.BLACKLIST: blacklist_str,
                CreateHashKeyAlgorithm.USER_AGENT: self.lne_user_agent.text(),
                CreateHashKeyAlgorithm.REFERER: self.lne_referer.text(),
            }
        return {
            CreateOAuthKeyAlgorithm.NAME: self.lne_name.text(),
            CreateOAuthKeyAlgorithm.WHITELIST: whitelist_str,
            CreateOAuthKeyAlgorithm.BLACKLIST: blacklist_str,
            CreateOAuthKeyAlgorithm.USER_AGENT: self.lne_user_agent.text(),
            CreateOAuthKeyAlgorithm.REFERER: self.lne_referer.text(),
        }

    def get_creation_algo_str(self) -> str:
        """Get algorithm name for user key creation

        :return: algorithm name
        :rtype: str
        """
        if self.rbtn_basic.isChecked():
            return f"{GeoplateformeProvider().id()}:{CreateBasicKeyAlgorithm().name()}"
        elif self.rbtn_hash.isChecked():
            return f"{GeoplateformeProvider().id()}:{CreateHashKeyAlgorithm().name()}"
        return f"{GeoplateformeProvider().id()}:{CreateOAuthKeyAlgorithm().name()}"

    def get_selected_permission_and_offering(
        self,
    ) -> list[Tuple[Permission, list[Offering]]]:
        """Return permission and offering with wanted checked status

        :param checked: wanted check status, defaults to True
        :type checked: bool, optional
        :return: list of permission and selected offering
        :rtype: list[Tuple[Permission, list[Offering]]]
        """
        return self.mdl_user_permission.get_checked_permission_and_offering(
            checked=True
        )

    def _qgis_auth_creation_possible(self) -> bool:
        """Check if qgis auth creation is possible

        :return: True if auth is basic or hash, False otherwise
        :rtype: bool
        """
        return self.rbtn_basic.isChecked() or self.rbtn_hash.isChecked()

    def create_qgis_auth(self, result: dict[str, Any]) -> None:
        """Ask user for qgis auth creation

        :param result: user key creation result, needed to get hash value
        :type result: dict[str, Any]
        """
        if not self._qgis_auth_creation_possible():
            return

        reply = QMessageBox.question(
            self,
            self.tr("Création authentification QGIS"),
            self.tr(
                "Voulez vous créer une configuration d'authentification QGIS pour cette clé ?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.rbtn_basic.isChecked():
                auth_config = UserKey.create_basic_auth_config(
                    name=self.lne_name.text(),
                    user=self.lne_login.text(),
                    password=self.lne_password.text(),
                )
            elif self.rbtn_hash.isChecked():
                auth_config = UserKey.create_hash_auth_config(
                    name=self.lne_name.text(),
                    hash=result[CreateHashKeyAlgorithm.CREATED_HASH],
                )

            auth_manager = QgsApplication.authManager()
            auth_created = auth_manager.storeAuthenticationConfig(auth_config, True)
            if not auth_created[0]:
                QMessageBox.warning(
                    self,
                    self.tr("Erreur lors de la création de l'authentification QGIS."),
                    self.tr(
                        "La configuration d'authentification QGIS n'a pas été correctement ajouté.\nVous devez ajouter manuellement la configuration."
                    ),
                )
