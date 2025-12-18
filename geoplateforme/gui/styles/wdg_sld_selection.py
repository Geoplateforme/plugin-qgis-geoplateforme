# standard
import os
import tempfile

from qgis.core import Qgis, QgsSldExportContext
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QWidget

# PyQGIS
from qgis.PyQt.QtXml import QDomDocument
from qgis.utils import OverrideCursor

from geoplateforme.gui.dlg_processing_run import ProcessingRunDialog

# Project
from geoplateforme.processing.provider import GeoplateformeProvider
from geoplateforme.processing.tools.sld_downgrade import SldDowngradeAlgorithm


class SldSelectionWidget(QWidget):
    def __init__(
        self,
        parent=None,
    ):
        """
        QWidget to select a sld file

        Args:
            parent: parent None

        """

        super().__init__(parent)

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_sld_selection.ui"),
            self,
        )

        # Display only vector layer with geometry
        self.cbx_layer.setFilters(
            Qgis.LayerFilter.VectorLayer & ~Qgis.LayerFilter.NoGeometry
        )

        # Update display page with radiobutton
        self.rbtn_sld_file.toggled.connect(self._selection_type_updated)
        self.rbtn_vector_layer.toggled.connect(self._selection_type_updated)

    def get_selected_stl_file(self) -> str:
        """Get selected sld file.
        If maplayer is selected, current style is exported as sdl and downgraded to 1.0.0 version.

        :return: selected sld file
        :rtype: str
        """
        if self.rbtn_sld_file.isChecked():
            return self.wdg_stl_file.filePath()
        else:
            return self._export_selected_layer_sld_to_tempfile()

    def _export_selected_layer_sld_to_tempfile(self) -> str:
        """Export selected layer to a temporary sld file downgraded to 1.0.0 version

        :return: created temporary sld file, empty str in case of error
        :rtype: str
        """

        layer = self.cbx_layer.currentLayer()
        if not layer:
            QMessageBox.critical(
                self,
                self.tr("Création .sld"),
                self.tr("Veuillez sélectionner une couche pour la création du sld."),
            )
            return ""

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            # Use temporary file for 1.1.0 .sld creation with QGIS export
            qgis_sld_file_output = tempfile.NamedTemporaryFile(
                delete=False, suffix="1_1_0.sld", mode="w", encoding="utf-8"
            )

            # Create Sld export context
            context = QgsSldExportContext()
            context.setExportFilePath(qgis_sld_file_output.name)
            context.setVendorExtension(
                Qgis.SldExportVendorExtension.GeoServerVendorExtension
            )
            context.setExportOptions(Qgis.SldExportOption.NoOptions)

            version_int = Qgis.versionInt()

            # Empty error message
            error_msg = ""
            if version_int > 34400:
                doc = layer.exportSldStyleV3(
                    exportContext=context,
                )
                error_msg = "\n".join(context.errors())
            else:
                # Empty QDomDocument
                doc = QDomDocument()

                layer.exportSldStyleV2(
                    doc=doc,
                    errorMsg=error_msg,
                    exportContext=context,
                )

            if error_msg:
                QMessageBox.critical(
                    self,
                    self.tr("Création .sld"),
                    self.tr(
                        "Le fichier .sld n'a pas pu être exporté depuis la couche vectorielle:\n {}"
                    ).format(error_msg),
                )
                return ""

            # Write content to output file
            sld_xml = doc.toString()
            qgis_sld_file_output.write(sld_xml)
            qgis_sld_file_output.close()

            output_file = tempfile.NamedTemporaryFile(
                delete=False, suffix="1_0_0.sld", mode="w", encoding="utf-8"
            )

            # Convert to 1.0.0 version of sld
            params = {
                SldDowngradeAlgorithm.FILE_PATH: qgis_sld_file_output.name,
                SldDowngradeAlgorithm.CHECK_INPUT: False,
                SldDowngradeAlgorithm.CHECK_OUTPUT: False,
                SldDowngradeAlgorithm.OUTPUT: output_file.name,
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{SldDowngradeAlgorithm().name()}"
            )
            run_dialog = ProcessingRunDialog(
                alg_name=algo_str,
                params=params,
                title=self.tr("Downgrade .sld for layer {}").format(layer.name()),
                parent=self,
            )
            run_dialog.exec()
            success, result = run_dialog.processing_results()
            if not success:
                QMessageBox.critical(
                    self,
                    self.tr("Conversion .sld"),
                    self.tr(
                        "Le fichier .sld n'a pas pu être converti au format 1.0.0:\n {}"
                    ).format(run_dialog.get_feedback().textLog()),
                )
            else:
                return result[SldDowngradeAlgorithm.OUTPUT]

        return ""

    def _selection_type_updated(self) -> None:
        """Change displayed page when selection type is changed"""
        if self.rbtn_sld_file.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_sld)
        else:
            self.stacked_widget.setCurrentWidget(self.page_layer)
