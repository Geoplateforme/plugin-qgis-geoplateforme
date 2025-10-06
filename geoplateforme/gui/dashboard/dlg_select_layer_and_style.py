from typing import List

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)


class SelectLayerAndStyleDialog(QDialog):
    def __init__(self, layers: List[dict], styles: List[dict]):
        super().__init__()

        self.setWindowTitle(self.tr("Choose Layer"))

        QBtn = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message_layer = QLabel(
            self.tr("<b>Please choose between available layers.</b>")
        )
        self.layer_combo = QComboBox()
        for layer in layers:
            self.layer_combo.addItem(layer["name"])

        message_style = QLabel(
            self.tr("<b>Please choose between available styles.</b>")
        )
        self.style_combo = QComboBox()
        self.style_combo.addItem(None)
        for style in styles:
            self.style_combo.addItem(style["name"])

        layout.addWidget(message_layer)
        layout.addWidget(self.layer_combo)
        layout.addWidget(message_style)
        layout.addWidget(self.style_combo)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
