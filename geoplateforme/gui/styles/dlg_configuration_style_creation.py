import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QWidget

from geoplateforme.api.configuration import Configuration, ConfigurationType
from geoplateforme.gui.dlg_processing_run import ProcessingRunDialog
from geoplateforme.gui.styles.wdg_mapbox_style_creation import MapboxStyleCreationWidget
from geoplateforme.gui.styles.wdg_wfs_style_creation import WfsStyleCreationWidget
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.style.add_configuration_style import (
    AddConfigurationStyleAlgorithm,
)


class ConfigurationStyleCreationDialog(QDialog):
    def __init__(self, configuration: Configuration, parent: QWidget):
        """
        QDialog for permission creation

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)

        uic.loadUi(
            os.path.join(
                os.path.dirname(__file__), "dlg_configuration_style_creation.ui"
            ),
            self,
        )
        self._configuration = configuration
        self._style_widget = None
        if configuration.type == ConfigurationType.WFS:
            self._style_widget = WfsStyleCreationWidget(self)
            self._style_widget.set_configuration(configuration)
            self.lyt_style_creation.addWidget(self._style_widget)
        else:
            self._style_widget = MapboxStyleCreationWidget(self)
            self.lyt_style_creation.addWidget(self._style_widget)
        self.setWindowTitle(self.tr("Création d'un style"))

    def accept(self) -> None:
        """Create configuration style from widget.
        Dialog is not closed if an error occurs during creation
        """
        algo_str = (
            f"{GeoplateformeProvider().id()}:{AddConfigurationStyleAlgorithm().name()}"
        )
        params = {
            AddConfigurationStyleAlgorithm.DATASTORE_ID: self._configuration.datastore_id,
            AddConfigurationStyleAlgorithm.CONFIGURATION_ID: self._configuration._id,
            AddConfigurationStyleAlgorithm.STYLE_NAME: self._style_widget.get_style_name(),
            AddConfigurationStyleAlgorithm.STYLE_FILE_PATHS: ",".join(
                self._style_widget.get_style_file_path()
            ),
            AddConfigurationStyleAlgorithm.DATASET_NAME: self._configuration.tags[
                "datasheet_name"
            ],
        }
        layer_style_names = self._style_widget.get_layer_style_names()
        if layer_style_names:
            params[AddConfigurationStyleAlgorithm.LAYER_STYLE_NAMES] = ",".join(
                layer_style_names
            )

        run_dialog = ProcessingRunDialog(
            alg_name=algo_str,
            params=params,
            title=self.tr("Adding configuration style"),
            parent=self,
        )
        run_dialog.exec()
        success, _ = run_dialog.processing_results()
        if not success:
            QMessageBox.warning(
                self,
                self.tr("Erreur lors de la création des styles."),
                run_dialog.get_feedback().textLog(),
            )
            return None

        return super().accept()
