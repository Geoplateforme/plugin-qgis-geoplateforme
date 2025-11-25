# standard
import sys

from qgis.core import QgsProcessingFeedback
from qgis.PyQt import sip
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QTextEdit


class QTextEditProcessingFeedBack(QgsProcessingFeedback):
    insert_text_color = pyqtSignal(str, QColor)

    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self._text_edit = text_edit
        if sys.platform.startswith("win"):
            self._text_edit.setFontFamily("Courier New")
        else:
            self._text_edit.setFontFamily("monospace")

        self._text_edit.setReadOnly(True)
        self._text_edit.setUndoRedoEnabled(False)

        self.insert_text_color.connect(self._change_color_and_insert_text)

    def setProgressText(self, text: str):
        super().setProgressText(text)
        self.pushInfo(text)

    def pushWarning(self, warning: str):
        super().pushWarning(warning)
        self.insert_text_color.emit(warning, QColor("orange"))

    def pushInfo(self, info: str):
        super().pushInfo(info)
        self.insert_text_color.emit(info, QColor("black"))

    def pushCommandInfo(self, info: str):
        super().pushCommandInfo(info)
        self.pushInfo(info)

    def pushDebugInfo(self, info):
        super().pushDebugInfo(info)
        self.pushInfo(info)

    def pushConsoleInfo(self, info: str):
        super().pushCommandInfo(info)
        self.pushInfo(info)

    def reportError(self, error: str, fatalError=False):
        super().reportError(error)
        self.insert_text_color.emit(error, QColor("red"))

    @pyqtSlot(str, QColor)
    def _change_color_and_insert_text(self, text: str, color: QColor):
        # We can have a feedback using a deleted text edit
        # Need to check if object is not deleted
        if not self._text_edit or sip.isdeleted(self._text_edit):
            return
        self._text_edit.setTextColor(color)
        self._text_edit.append(text)
        sb = self._text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
