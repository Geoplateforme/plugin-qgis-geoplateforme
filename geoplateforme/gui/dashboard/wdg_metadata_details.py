import os

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget

from geoplateforme.api.metadata import Metadata


class MetadataDetailsWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        """
        QWidget to display metadata details

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_metadata_details.ui"),
            self,
        )

    def setMetadata(self, metadata: Metadata, datastore_id: str):
        """
        Fill widget with metadata

        :param metadata: the metadata
        :type metadata: Metadata
        :param datastore_id: datastore id
        :type datastore_id: str
        """
        self.le_title.setText(metadata.fields.title)
        self.te_description.setText(metadata.fields.abstract)
        self.le_context.setText(datastore_id)
        self.le_unique_id.setText(metadata.fields.identifier)
        self.le_thematics.setText(", ".join(metadata.fields.topics))
        self.le_inspire_kw.setText(", ".join(metadata.fields.inspire_keywords))
        self.le_kw.setText(", ".join(metadata.fields.free_keywords))

        if metadata.fields.bbox is not None:
            extent = QgsRectangle(
                metadata.fields.bbox["xmin"],
                metadata.fields.bbox["ymin"],
                metadata.fields.bbox["xmax"],
                metadata.fields.bbox["ymax"],
            )
            self.gbp_bbox.setCurrentExtent(
                extent, QgsCoordinateReferenceSystem("EPSG:4326")
            )

        self.le_genealogy.setText(metadata.fields.genealogy)
        self.de_creation_date.setDate(metadata.fields.creation_date)
        self.le_frequency.setText(metadata.fields.frequency)
