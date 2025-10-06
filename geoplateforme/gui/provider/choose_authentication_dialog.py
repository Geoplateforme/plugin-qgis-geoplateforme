from typing import Optional

from qgis.gui import QgsAuthConfigSelect, QgsCollapsibleGroupBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from qgis.utils import iface, plugins

from geoplateforme.gui.user_keys.dlg_user_keys import UserKeysDialog


class ChooseAuthenticationDialog(QDialog):
    def __init__(self, metadata_link: Optional[str] = None):
        super().__init__()

        self.dlg_user_keys = None

        self.setWindowTitle(self.tr("Choose authentication"))

        QBtn = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(
            self.tr(
                "<b>This data is private, please choose a valid authentication configuration.</b>"
            )
        )
        self.authent = QgsAuthConfigSelect()
        self.authent.setObjectName("authent")

        link = ""
        if metadata_link is not None:
            link = (
                f': <a href="{metadata_link}">' + self.tr("link to metadata") + "</a>"
            )

        gb_information = QgsCollapsibleGroupBox("Informations")
        information_layout = QVBoxLayout(gb_information)
        information_message = QLabel(
            self.tr("Please contact data producer for grant access")
            + link
            + self.tr("<br><br>If you already have grant access in geoplateforme,<br>")
            + self.tr("authentication configuration can be generate here :")
        )
        # information_message.setTextFormat(Qt.RichText)
        # information_message.setTextInteractionFlags(Qt.TextBrowserInteraction);
        information_message.setOpenExternalLinks(True)

        btn_user_keys = QPushButton(self.tr("User keys configuration"))
        btn_user_keys.setIcon(QIcon(":images/themes/default/locked.svg"))
        btn_user_keys.clicked.connect(self.user_key_configuration)
        information_layout.addWidget(information_message)
        information_layout.addWidget(btn_user_keys)
        layout.addWidget(message)
        layout.addWidget(self.authent)
        layout.addWidget(gb_information)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def user_key_configuration(self):
        geoplateforme_plugin = plugins["geoplateforme"]
        if geoplateforme_plugin.dlg_user_keys is None:
            geoplateforme_plugin.dlg_user_keys = UserKeysDialog(iface.mainWindow())
        geoplateforme_plugin.dlg_user_keys.refresh()
        geoplateforme_plugin.dlg_user_keys.show()
        self.reject()
