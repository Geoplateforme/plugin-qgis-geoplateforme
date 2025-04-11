#! python3  # noqa: E265

"""
Common GUI utils.
"""

# standard
from typing import Union

# PyQGIS
from qgis.PyQt.QtCore import QCoreApplication, QEvent, Qt
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication, QLabel, QLineEdit, QWidget

# plugin
from geoplateforme.toolbelt import PlgLogger


class GuiCommonUtils:
    """
    Common GUI utils.
    """

    def copy_widget_txt_to_clipboard(
        self, wdg_source: QWidget, custom_log_header: str = None
    ) -> bool:
        """Copy source widget content into the system clipboard.

        :param wdg_source: widget source. Accepts only QLabel or QLineEdit.
        :type wdg_source: QWidget
        :param custom_log_header: customize the log header, defaults to None
        :type custom_log_header: str, optional

        :return: True if content has been copied
        :rtype: bool
        """
        # quick checks
        if not isinstance(wdg_source, (QLabel, QLineEdit)):
            return False
        if len(wdg_source.text().strip()) == 0:
            return False

        # load content into clipboard
        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(wdg_source.text(), mode=cb.Clipboard)

        # Refine the log message
        if custom_log_header:
            log_msg = custom_log_header
        elif isinstance(wdg_source, QLabel) and wdg_source.buddy():
            log_msg = wdg_source.buddy().text()
        else:
            log_msg = wdg_source.objectName()

        PlgLogger().log(
            message=log_msg + self.tr(" content has been copied into the clipboard."),
            push=True,
        )
        return True

    def make_qlabel_copiable(
        self, target_qlabel: QLabel, buddy_widget: Union[QLabel, QLineEdit] = None
    ) -> bool:
        """Make a QLabel being selectable and copiable by double-click.

        :param target_qlabel: QLabel to make copiable
        :type target_qlabel: QWidget
        :param buddy_widget: widget to set as buddy to use later as display text, defaults to None
        :type buddy_widget: QWidget, optional

        :return: True if QLabel is copiable
        :rtype: bool
        """
        # quick checks
        if not isinstance(target_qlabel, QLabel):
            return False
        if not isinstance(buddy_widget, (QLabel, QLineEdit)):
            return False

        target_qlabel.setBuddy(buddy_widget)
        target_qlabel.setToolTip(
            self.tr("Double-click me to copy my content into the clipboard.")
        )
        target_qlabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        target_qlabel.setCursor(QCursor(Qt.CursorShape.IBeamCursor))

        # connect event filter
        target_qlabel.parent().eventFilter = self.eventFilter
        target_qlabel.installEventFilter(target_qlabel.parent())

        return True

    def eventFilter(self, source: QWidget, event: QEvent) -> bool:
        """Custom event filter to handle special user actions. Can override any widget
        interaction.

        :param source: widget which emitted the event
        :type source: QWidget
        :param event: event type
        :type event: QEvent

        :return: True if event has been handled. Note: retun bool is mandatory.
        :rtype: bool
        """
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.copy_widget_txt_to_clipboard(source)
            return True
        return False

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)
