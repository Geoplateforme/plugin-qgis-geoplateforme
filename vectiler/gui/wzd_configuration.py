# standard

import os

from PyQt5 import QtCore, QtGui, uic

# PyQGIS
from qgis.PyQt.QtWidgets import QListWidgetItem, QWizard


class WzdConfiguration(QWizard):
    def __init__(self, parent=None):

        """
        Dialog to define current geotuileur configuration data

        Args:
            parent: parent QObject
        """

        super().__init__(parent)
        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wzd_configuration.ui"), self
        )

        # To avoid some characters

        rx = QtCore.QRegExp("[a-z-A-Z-0-9-_]+")
        validator = QtGui.QRegExpValidator(rx)
        self.lne_flux.setValidator(validator)

        # Choose available attributes only for demo

        attributs = [
            {
                "Name": "Vegetation",
                "State": "Checked",
            },
            {
                "Name": "Cities",
                "State": "Unchecked",
            },
            {
                "Name": "Categories",
                "State": "Unchecked",
            },
            {
                "Name": "Creation date",
                "State": "Unchecked",
            },
            {
                "Name": "Toponym",
                "State": "Unchecked",
            },
            {
                "Name": "Cleabs",
                "State": "Checked",
            },
            {
                "Name": "Fid",
                "State": "Unchecked",
            },
            {
                "Name": "Nature",
                "State": "Checked",
            },
        ]

        for i in range(len(attributs)):
            self.item = QListWidgetItem()
            self.item.setText(attributs[i]["Name"])
            self.item.setFont(QtGui.QFont("Arial", 13))
            self.item.setFlags(self.item.flags() | QtCore.Qt.ItemIsUserCheckable)
            if attributs[i]["State"] == "Unchecked":
                self.item.setCheckState(QtCore.Qt.Unchecked)
                self.lwg_attribut.addItem(self.item)
            else:
                self.item.setCheckState(QtCore.Qt.Checked)
                self.lwg_attribut.addItem(self.item)
