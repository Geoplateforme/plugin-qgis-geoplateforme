from qgis.PyQt.QtCore import QRegularExpression
from qgis.PyQt.QtGui import QRegularExpressionValidator
from qgis.PyQt.QtWidgets import QLineEdit


class IpCIDRLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Regex for IPv4/CIDR
        cidr_regex = QRegularExpression(
            r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"/(3[0-2]|[1-2]?\d)$"
        )

        self.validator = QRegularExpressionValidator(cidr_regex, self)

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
                    "Cette plage d’IP doit être au format CIDR "
                    "(exemples: 192.168.1.1/32, 192.168.0.1/24)"
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
