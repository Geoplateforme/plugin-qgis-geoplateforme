import typing

from PyQt5 import QtCore
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QStandardItemModel


class CheckStateModel(QStandardItemModel):
    """
    QStandardItemModel TreeModel implementation for automatic check of child and parent
    Add itemCheckStateChanged(QModelIndex) signal
    """

    # Signal emitted when delimiter is changed.
    itemCheckStateChanged = QtCore.pyqtSignal(QModelIndex)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """
        Override QStandardItemModel flags.

        Args:
            index: QModelIndex

        Returns: index flags

        """
        # All item should be checkable
        flags = super().flags(index)
        flags = flags | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate
        return flags

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = Qt.DisplayRole) -> bool:
        """
        Override QStandardItemModel setData for child and parent CheckStateRole synchronization.

        Args:
            index: QModelIndex
            value: new value
            role: Qt role

        Returns: True if data set, False otherwise

        """

        if role == Qt.CheckStateRole:
            newState = value
            oldState = self.data(index, role)

            # define new state
            res = super().setData(index, value, role)

            # emit signal if check state changed
            if newState != oldState:
                self.itemCheckStateChanged.emit(index)

            checked = newState == Qt.Checked

            # update children CheckStateRole
            self.setChildrenChecked(index, checked)

            # update parent if valid and checkable
            parent = index.parent()
            if parent.isValid() and self.flags(parent) & Qt.ItemIsAutoTristate:
                if super().data(parent, Qt.CheckStateRole) is not None:
                    super().setData(parent, self.childrenCheckState(parent), role)
        else:
            res = super().setData(index, value, role)

        return res

    def setChildrenChecked(self, parent: QModelIndex, checked: bool) -> None:
        """
        Update check state of parent child

        Args:
            parent: parent QModelIndex
            checked: (bool) parent is checked
        """
        for i in range(0, self.rowCount(parent)):
            index = self.index(i, 0, parent)
            if index.isValid():
                check_state = Qt.Checked if checked else Qt.Unchecked
                self.setData(index, check_state, Qt.CheckStateRole)

    def childrenCheckState(self, parent: QModelIndex) -> Qt.CheckState:
        """
        Define parent CheckState from children CheckStateRole

        Args:
            parent: parent QModelIndex

        Returns: Qt.CheckState

        """
        total = self.rowCount(parent)
        nb_checked = 0
        nb_unchecked = 0

        for i in range(0, self.rowCount(parent)):
            check_state = self.data(parent.child(i, 0), Qt.CheckStateRole)
            if check_state == Qt.Checked:
                nb_checked = nb_checked + 1
            else:
                nb_unchecked = nb_unchecked + 1

        if total == nb_checked:
            res = Qt.Checked
        elif total == nb_unchecked:
            res = Qt.Unchecked
        else:
            res = Qt.PartiallyChecked
        return res
