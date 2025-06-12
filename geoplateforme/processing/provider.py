#! python3  # noqa: E265

"""
Processing provider module.
"""

# PyQGIS
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon

# project
from geoplateforme.__about__ import __icon_path__, __title__, __version__
from geoplateforme.processing.generation.create_raster_tiles_from_wms_vector import (
    RasterTilesFromWmsVectorAlgorithm,
)
from geoplateforme.processing.generation.tile_creation import TileCreationAlgorithm
from geoplateforme.processing.generation.upload_database_integration import (
    UploadDatabaseIntegrationAlgorithm,
)
from geoplateforme.processing.publication.upload_publication import (
    UploadPublicationAlgorithm,
)
from geoplateforme.processing.publication.wfs_publication import WfsPublicationAlgorithm
from geoplateforme.processing.publication.wms_publication import WmsPublicationAlgorithm
from geoplateforme.processing.publication.wms_raster_publication import (
    WmsRasterPublicationAlgorithm,
)
from geoplateforme.processing.publication.wmts_publication import (
    WmtsPublicationAlgorithm,
)
from geoplateforme.processing.tools.check_layer import CheckLayerAlgorithm
from geoplateforme.processing.tools.create_geoserver_style import (
    CreateGeoserverStyleAlgorithm,
)
from geoplateforme.processing.tools.delete_stored_data import DeleteStoredDataAlgorithm
from geoplateforme.processing.tools.delete_upload import DeleteUploadAlgorithm
from geoplateforme.processing.tools.sld_downgrade import SldDowngradeAlgorithm
from geoplateforme.processing.unpublish import UnpublishAlgorithm
from geoplateforme.processing.update_tile_upload import UpdateTileUploadAlgorithm
from geoplateforme.processing.upload.upload_from_files import GpfUploadFromFileAlgorithm
from geoplateforme.processing.upload.upload_from_layers import (
    GpfUploadFromLayersAlgorithm,
)
from geoplateforme.processing.vector_db_creation import VectorDatabaseCreationAlgorithm

# ############################################################################
# ########## Classes ###############
# ##################################


class GeoplateformeProvider(QgsProcessingProvider):
    """
    Processing provider class.
    """

    def loadAlgorithms(self):
        """Loads all algorithms belonging to this provider."""
        self.addAlgorithm(CheckLayerAlgorithm())
        self.addAlgorithm(GpfUploadFromFileAlgorithm())
        self.addAlgorithm(UploadDatabaseIntegrationAlgorithm())
        self.addAlgorithm(VectorDatabaseCreationAlgorithm())
        self.addAlgorithm(TileCreationAlgorithm())
        self.addAlgorithm(UploadPublicationAlgorithm())
        self.addAlgorithm(UnpublishAlgorithm())
        self.addAlgorithm(UpdateTileUploadAlgorithm())
        self.addAlgorithm(DeleteStoredDataAlgorithm())
        self.addAlgorithm(DeleteUploadAlgorithm())
        self.addAlgorithm(GpfUploadFromLayersAlgorithm())
        self.addAlgorithm(WfsPublicationAlgorithm())
        self.addAlgorithm(CreateGeoserverStyleAlgorithm())
        self.addAlgorithm(SldDowngradeAlgorithm())
        self.addAlgorithm(WmsPublicationAlgorithm())
        self.addAlgorithm(RasterTilesFromWmsVectorAlgorithm())
        self.addAlgorithm(WmsRasterPublicationAlgorithm())
        self.addAlgorithm(WmtsPublicationAlgorithm())

    def id(self) -> str:
        """Unique provider id, used for identifying it. This string should be unique, \
        short, character only string, eg "qgis" or "gdal". \
        This string should not be localised.

        :return: provider ID
        :rtype: str
        """
        return "geoplateforme"

    def name(self) -> str:
        """Returns the provider name, which is used to describe the provider
        within the GUI. This string should be short (e.g. "Lastools") and localised.

        :return: provider name
        :rtype: str
        """
        return __title__

    def longName(self) -> str:
        """Longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools". This string should be localised. The default
        implementation returns the same string as name().

        :return: provider long name
        :rtype: str
        """
        return self.tr("Geoplateforme - Tools")

    def icon(self) -> QIcon:
        """QIcon used for your provider inside the Processing toolbox menu.

        :return: provider icon
        :rtype: QIcon
        """
        return QIcon(str(__icon_path__))

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def versionInfo(self) -> str:
        """Version information for the provider, or an empty string if this is not \
        applicable (e.g. for inbuilt Processing providers). For plugin based providers, \
        this should return the plugin’s version identifier.

        :return: version
        :rtype: str
        """
        return __version__
