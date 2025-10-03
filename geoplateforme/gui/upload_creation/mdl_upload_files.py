from pathlib import Path
from typing import List

from osgeo import ogr
from qgis.core import QgsApplication, QgsMapLayerModel, QgsVectorLayer
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QObject, Qt, QVariant
from qgis.PyQt.QtGui import QIcon, QStandardItemModel

from geoplateforme.toolbelt import PlgLogger


class UploadFilesTreeModel(QStandardItemModel):
    NAME_COL = 0
    CSR_COL = 1
    ID_COL = 2

    def __init__(self, parent: QObject = None):
        """QStandardItemModel for upload file and layer list display

        :param parent: parent, defaults to None
        :type parent: QObject, optional
        """
        super().__init__(parent)
        self.log = PlgLogger().log
        self.setHorizontalHeaderLabels(
            [
                self.tr("Name"),
                self.tr("CRS"),
            ]
        )

    def get_filenames(self) -> List[str]:
        """Get displayed filename list

        :return: filename list
        :rtype: List[str]
        """
        layers = []
        for row in range(0, self.rowCount()):
            layer = self.data(self.index(row, self.NAME_COL), Qt.ItemDataRole.UserRole)
            if isinstance(layer, str):
                layers.append(layer)
        return layers

    def get_layers(self) -> List[QgsVectorLayer]:
        """Get displayed layer list

        :return: layer list
        :rtype: List[QgsVectorLayer]
        """
        layers = []
        for row in range(0, self.rowCount()):
            layer = self.data(self.index(row, self.NAME_COL), Qt.ItemDataRole.UserRole)
            if isinstance(layer, QgsVectorLayer):
                layers.append(layer)
        return layers

    def get_first_displayed_name(self) -> str:
        """Get first displayed name

        :return: first display name defined
        :rtype: str
        """
        row = self.rowCount()
        if row > 0:
            layer = self.data(self.index(0, self.NAME_COL), Qt.ItemDataRole.UserRole)
            if isinstance(layer, QgsVectorLayer):
                return layer.name()
            elif isinstance(layer, str):
                return layer
            return ""
        else:
            return ""

    def get_first_crs(self) -> str:
        """Get first defined crs auth id, empty str if no crs defined

        :return: first defined crs
        :rtype: str
        """
        result = ""

        # For all files
        for row in range(0, self.rowCount()):
            parent = self.index(row, self.NAME_COL)

            crs = self.data(self.index(row, self.CSR_COL))
            if crs:
                result = crs
                # break for layers in file
                break

            # Get first defined crs
            for layer_row in range(0, self.rowCount(parent)):
                crs = self.data(self.index(layer_row, self.CSR_COL, parent))
                if crs:
                    result = crs
                    # break for layers in file
                    break
            # Break if a crs was defined in this file
            if result:
                break
        return result

    def data(
        self, index: QtCore.QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> QVariant:
        """Override QStandardItemModel data() for :
        - decoration role for CRS icon if invalid value

        :param index: QModelIndex
        :type index: QtCore.QModelIndex
        :param role: Qt Rpme, defaults to Qt.ItemDataRole.DisplayRole
        :type role: int, optional
        :return: data for wanted rol
        :rtype: QVariant
        """
        result = super().data(index, role)

        if role == Qt.ItemDataRole.DecorationRole:
            if index.column() == self.CSR_COL:
                crs = self.data(index, Qt.ItemDataRole.DisplayRole)
                if crs:
                    first_crs = self.get_first_crs()
                    valid = ("EPSG:" in crs or "IGNF" in crs) and crs == first_crs
                    if valid:
                        result = QIcon(QgsApplication.iconPath("mIconSuccess.svg"))
                    else:
                        result = QIcon(QgsApplication.iconPath("mIconWarning.svg"))
        elif role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == self.CSR_COL:
                crs = self.data(index, Qt.ItemDataRole.DisplayRole)
                if crs:
                    first_crs = self.get_first_crs()
                    valid = "EPSG:" in crs or "IGNF" in crs
                    if not valid:
                        result = self.tr(
                            "Invalid CRS. Only EPSG and IGNF crs are supported."
                        )
                    elif crs != first_crs:
                        result = self.tr("Invalid CRS {0}. Expected {1}").format(
                            crs, first_crs
                        )
        return result

    def clear_values(self) -> None:
        """Clear all values"""
        while self.rowCount():
            self.removeRow(0)

    def add_file(self, filename: str) -> None:
        """
        Add file to model

        Args:
            filename: (str) file name
        """
        self._insert_file(filename)

    def add_layer(self, layer: QgsVectorLayer) -> None:
        """Add layer to table

        :param layer: layer to add
        :type layer: QgsVectorLayer
        """
        row = self.rowCount()
        self.insertRow(row)
        self.setData(self.index(row, self.NAME_COL), layer, Qt.ItemDataRole.UserRole)
        self.setData(
            self.index(row, self.NAME_COL),
            QgsMapLayerModel.iconForLayer(layer),
            Qt.ItemDataRole.DecorationRole,
        )
        storage_type = layer.storageType()
        if storage_type == "ESRI Shapefile" or storage_type == "GeoJSON":
            self.setData(self.index(row, self.NAME_COL), Path(layer.source()).stem)
        else:
            self.setData(self.index(row, self.NAME_COL), layer.name())
        self.setData(self.index(row, self.CSR_COL), layer.crs().authid())

    def _insert_file(self, filename: str) -> None:
        """Insert file and add layers as children. If file doesn't exist it's not added

        :param filename: filename
        :type filename: str
        """
        row = self.rowCount()
        self.insertRow(row)

        fileinfo = QtCore.QFileInfo(filename)

        self.setData(self.index(row, self.NAME_COL), filename)
        self.setData(self.index(row, self.NAME_COL), filename, Qt.ItemDataRole.UserRole)
        parent = self.index(row, self.NAME_COL)

        if not fileinfo.exists():
            icon = QIcon(QgsApplication.iconPath("mIconWarning.svg"))
        elif fileinfo.suffix() == "gpkg":
            icon = QIcon(QgsApplication.iconPath("mGeoPackage.svg"))
        elif fileinfo.suffix() == "zip":
            icon = QIcon(QgsApplication.iconPath("mIconZip.svg"))
        else:
            icon = QIcon(QgsApplication.iconPath("mIconFile.svg"))

        self.setData(
            self.index(row, self.NAME_COL), icon, Qt.ItemDataRole.DecorationRole
        )

        self.insertColumns(0, self.columnCount(), parent)

        # Load layers from gpkg
        if fileinfo.exists() and fileinfo.suffix() == "gpkg":
            for layer in ogr.Open(filename):
                layer_name = layer.GetName()
                layer = QgsVectorLayer(f"{filename}|layername={layer_name}", layer_name)
                if layer.isValid():
                    row = self.rowCount(parent)
                    self.insertRow(row, parent)
                    self.setData(self.index(row, self.NAME_COL, parent), layer_name)
                    self.setData(
                        self.index(row, self.CSR_COL, parent), layer.crs().authid()
                    )
