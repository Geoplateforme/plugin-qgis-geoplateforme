import logging
from dataclasses import dataclass

from qgis.PyQt.QtCore import QRect, Qt, pyqtSignal
from qgis.PyQt.QtGui import QBrush, QColor, QPainter, QPalette
from qgis.PyQt.QtWidgets import QSizePolicy, QWidget


def _left_thumb_adjuster(value, min_value):
    value = max(value, min_value)


def _right_thumb_adjuster(value, max_value):
    value = min(value, max_value)


def _set_painter_pen_color(painter, pen_color):
    pen = painter.pen()
    pen.setColor(pen_color)
    painter.setPen(pen)


@dataclass
class Thumb:
    """Thumb class which holds information about a thumb."""

    value: int
    rect: QRect
    pressed: bool


class QtRangeSlider(QWidget):
    """
    QtRangeSlider is a class which implements a slider with 2 thumbs.

    Methods

            * __init__ (self, QWidget parent, left_value, right_value, left_thumb_value=0, right_thumb_value=None)
            * set_left_thumb_value (self, int value):
            * set_right_thumb_value (self, int value):
            * (int) get_left_thumb_value (self):
            * (int) get_right_thumb_value (self):

    Signals

            * left_thumb_value_changed (int)
            * right_thumb_value_changed (int)

    """

    HEIGHT = 30
    WIDTH = 120
    THUMB_WIDTH = 16
    THUMB_HEIGHT = 16
    TRACK_HEIGHT = 3
    TRACK_COLOR = QColor(0xC7, 0xC7, 0xC7)
    TRACK_FILL_COLOR = QColor(0x01, 0x81, 0xFF)
    TRACK_PADDING = THUMB_WIDTH // 2 + 5
    TICK_PADDING = 5

    left_thumb_value_changed = pyqtSignal("unsigned long long")
    right_thumb_value_changed = pyqtSignal("unsigned long long")

    def __init__(
        self,
        parent,
        left_value,
        right_value,
        left_thumb_value=None,
        right_thumb_value=None,
    ):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(self.WIDTH)
        self.setMinimumHeight(self.HEIGHT)

        self._left_value = left_value
        self._right_value = right_value

        _left_thumb_value = (
            left_thumb_value if left_thumb_value is not None else self._left_value
        )
        self._left_thumb = Thumb(_left_thumb_value, None, False)
        _right_thumb_value = (
            right_thumb_value if right_thumb_value is not None else self._right_value
        )
        if _right_thumb_value < _left_thumb_value + 1:
            raise ValueError("Right thumb value is less or equal left thumb value.")
        self._right_thumb = Thumb(_right_thumb_value, None, False)

        self._range = self._right_value - self._left_value

        self._canvas_width = None
        self._canvas_height = None

        self._ticks_count = 0

        parent_palette = parent.palette()
        self._background_color = parent_palette.color(QPalette.ColorRole.Window)
        self._base_color = parent_palette.color(QPalette.ColorRole.Base)
        self._button_color = parent_palette.color(QPalette.ColorRole.Button)
        self._border_color = parent_palette.color(QPalette.ColorRole.Mid)

    def paintEvent(self, unused_e):
        logging.debug("paintEvent")
        del unused_e
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.__draw_track(self._canvas_width, self._canvas_height, painter)
        self.__draw_track_fill(self._canvas_width, self._canvas_height, painter)
        self.__draw_ticks(
            self._canvas_width, self._canvas_height, painter, self._ticks_count
        )
        self.__draw_left_thumb(self._canvas_width, self._canvas_height, painter)
        self.__draw_right_thumb(self._canvas_width, self._canvas_height, painter)

        painter.end()

    def __get_track_y_position(self):
        return self._canvas_height // 2 - self.TRACK_HEIGHT // 2

    def __draw_track(self, canvas_width, canvas_height, painter):
        del canvas_height
        brush = QBrush()
        brush.setColor(self.TRACK_COLOR)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        rect = QRect(
            self.TRACK_PADDING,
            self.__get_track_y_position(),
            canvas_width - 2 * self.TRACK_PADDING,
            self.TRACK_HEIGHT,
        )
        painter.fillRect(rect, brush)

    def __draw_track_fill(self, canvas_width, canvas_height, painter):
        del canvas_height
        brush = QBrush()
        brush.setColor(self.TRACK_FILL_COLOR)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        available_width = canvas_width - 2 * self.TRACK_PADDING
        x1 = (
            self._left_thumb.value - self._left_value
        ) / self._range * available_width + self.TRACK_PADDING
        x2 = (
            self._right_thumb.value - self._left_value
        ) / self._range * available_width + self.TRACK_PADDING
        rect = QRect(
            round(x1),
            self.__get_track_y_position(),
            round(x2) - round(x1),
            self.TRACK_HEIGHT,
        )
        painter.fillRect(rect, brush)

    def __draw_thumb(self, x, y, painter):
        brush = QBrush()
        brush.setColor(self._base_color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        _set_painter_pen_color(painter, self._border_color)

        painter.setBrush(brush)

        thumb_rect = QRect(
            round(x) - self.THUMB_WIDTH // 2 + self.TRACK_PADDING,
            y + self.TRACK_HEIGHT // 2 - self.THUMB_HEIGHT // 2,
            self.THUMB_WIDTH,
            self.THUMB_HEIGHT,
        )
        painter.drawEllipse(thumb_rect)
        return thumb_rect

    def __draw_right_thumb(self, canvas_width, canvas_height, painter):
        del canvas_height
        available_width = canvas_width - 2 * self.TRACK_PADDING
        x = round(
            (self._right_thumb.value - self._left_value) / self._range * available_width
        )
        y = self.__get_track_y_position()
        self._right_thumb.rect = self.__draw_thumb(x, y, painter)

    def __draw_left_thumb(self, canvas_width, canvas_height, painter):
        del canvas_height
        available_width = canvas_width - 2 * self.TRACK_PADDING
        x = round(
            (self._left_thumb.value - self._left_value) / self._range * available_width
        )
        y = self.__get_track_y_position()
        self._left_thumb.rect = self.__draw_thumb(x, y, painter)

    def set_left_thumb_value(self, value):
        if value < self._left_value or value > self._right_thumb.value - 1:
            return
        if value == self._left_thumb.value:
            # nothing to update
            return
        self._left_thumb.value = value
        # pylint: disable=logging-fstring-interpolation
        logging.debug(f"value before emit {value}")
        self.left_thumb_value_changed.emit(value)
        self.repaint()

    def set_right_thumb_value(self, value):
        if value > self._right_value or value < self._left_thumb.value + 1:
            return
        if value == self._right_thumb.value:
            # nothing to update
            return
        self._right_thumb.value = value
        # pylint: disable=logging-fstring-interpolation
        logging.debug(f"value before emit {value}")
        self.right_thumb_value_changed.emit(value)
        self.repaint()

    # override Qt event
    def mousePressEvent(self, event):
        logging.debug("mousePressEvent")
        position = event.pos()
        if self._left_thumb.rect.contains(int(position.x()), int(position.y())):
            self._left_thumb.pressed = True
        if self._right_thumb.rect.contains(int(position.x()), int(position.y())):
            self._right_thumb.pressed = True
        super().mousePressEvent(event)

    # override Qt event
    def mouseReleaseEvent(self, event):
        logging.debug("mouseReleaseEvent")
        self._left_thumb.pressed = False
        self._right_thumb.pressed = False
        super().mouseReleaseEvent(event)

    def __get_thumb_value(self, x, canvas_width, range):
        # pylint: disable=logging-fstring-interpolation
        logging.debug(
            f"x {x} canvas_width {canvas_width} left_value {self._left_thumb.value} right_value {range}"
        )
        return round(x / canvas_width * range)

    # override Qt event
    def mouseMoveEvent(self, event):
        logging.debug("mouseMoveEvent")

        thumb = self._left_thumb if self._left_thumb.pressed else self._right_thumb

        if thumb.pressed:
            if thumb == self._left_thumb:
                value_setter = self.set_left_thumb_value

                def value_adjuster(val):
                    return _left_thumb_adjuster(val, self._left_value)

            else:
                value_setter = self.set_right_thumb_value

                def value_adjuster(val):
                    return _right_thumb_adjuster(val, self._right_value)

            new_val = (
                self.__get_thumb_value(event.pos().x(), self._canvas_width, self._range)
                + self._left_value
            )
            print(new_val)
            value_adjuster(new_val)
            value_changed = new_val != thumb.value
            if value_changed:
                value_setter(new_val)

        super().mouseMoveEvent(event)

    def get_left_thumb_value(self):
        return self._left_thumb.value

    def get_right_thumb_value(self):
        return self._right_thumb.value

    def set_ticks_count(self, count):
        if count < 0:
            raise ValueError("Invalid ticks count.")
        self._ticks_count = count

    def __draw_ticks(self, canvas_width, canvas_height, painter, ticks_count):
        del canvas_height
        if not self._ticks_count:
            return

        _set_painter_pen_color(painter, self._border_color)

        tick_step = (canvas_width - 2 * self.TRACK_PADDING) // ticks_count
        y1 = self.__get_track_y_position() - self.TICK_PADDING
        y2 = y1 - self.THUMB_HEIGHT // 2
        for x in range(ticks_count + 1):
            x = x * tick_step + self.TRACK_PADDING
            painter.drawLine(x, y1, x, y2)

    def resizeEvent(self, event):
        logging.debug("resizeEvent")
        del event
        self._canvas_width = self.width()
        self._canvas_height = self.height()
