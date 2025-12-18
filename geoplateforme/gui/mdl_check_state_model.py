from typing import Any

from qgis.PyQt.QtCore import QModelIndex, Qt, pyqtSignal
from qgis.PyQt.QtGui import QStandardItemModel


class CheckStateModel(QStandardItemModel):
    """
    QStandardItemModel TreeModel implementation for automatic check of child and parent
    Add itemCheckStateChanged(QModelIndex) signal
    """

    # Signal emitted when delimiter is changed.
    itemCheckStateChanged = pyqtSignal(QModelIndex)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """
        Override QStandardItemModel flags.

        Args:
            index: QModelIndex

        Returns: index flags

        """
        # All item should be checkable
        flags = super().flags(index)
        flags = flags | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate
        return flags

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        """
        Override QStandardItemModel setData for child and parent CheckStateRole synchronization.

        Args:
            index: QModelIndex
            value: new value
            role: Qt role

        Returns: True if data set, False otherwise

        """

        if role == Qt.ItemDataRole.CheckStateRole:
            newState = value
            oldState = self.data(index, role)

            # define new state
            res = super().setData(index, value, role)

            # emit signal if check state changed
            if newState != oldState:
                self.itemCheckStateChanged.emit(index)

            checked = newState == Qt.CheckState.Checked

            # update children CheckStateRole
            self.setChildrenChecked(index, checked)

            # update parent if valid and checkable
            parent = index.parent()
            if parent.isValid() and self.flags(parent) & Qt.ItemFlag.ItemIsAutoTristate:
                if super().data(parent, Qt.ItemDataRole.CheckStateRole) is not None:
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
                check_state = (
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
                self.setData(index, check_state, Qt.ItemDataRole.CheckStateRole)

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
            index = self.index(i, 0, parent)
            check_state = self.data(index, Qt.ItemDataRole.CheckStateRole)
            if check_state == Qt.CheckState.Checked:
                nb_checked = nb_checked + 1
            else:
                nb_unchecked = nb_unchecked + 1

        if total == nb_checked:
            res = Qt.CheckState.Checked
        elif total == nb_unchecked:
            res = Qt.CheckState.Unchecked
        else:
            res = Qt.CheckState.PartiallyChecked
        return res
