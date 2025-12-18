from qgis.PyQt.QtCore import QRegularExpression
from qgis.PyQt.QtGui import QRegularExpressionValidator
from qgis.PyQt.QtWidgets import QLineEdit


class UUIDLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Regex for UUID
        uuid_regex = QRegularExpression(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        )

        self.validator = QRegularExpressionValidator(uuid_regex, self)

        # Check input during change
        self.editingFinished.connect(self._validate_input)
        self.textChanged.connect(self._validate_input)

    def _validate_input(self):
        """Update style sheet for invalid values"""
        text = self.text()
        if text and not self.valid():
            self.setStyleSheet("border: 2px solid red;")
            self.setToolTip(
                self.tr(
                    "La valeur doit être un UUID xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                )
            )
        else:
            self.setStyleSheet("")
            self.setToolTip("")

    def valid(self) -> bool:
        """Check if input IP is valid

        :return: True if IP is valid, False otherwise
        :rtype: bool
        """
        text = self.text()
        state, _, _ = self.validator.validate(text, 0)
        if state != QRegularExpressionValidator.State.Acceptable:
            return False
        return True
