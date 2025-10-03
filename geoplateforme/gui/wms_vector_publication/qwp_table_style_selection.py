# standard
import os

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QWizardPage
from qgis.utils import OverrideCursor

from geoplateforme.api.configuration import WmsVectorTableStyle
from geoplateforme.api.stored_data import StoredData
from geoplateforme.gui.wms_vector_publication.wdg_table_style_selection import (
    TableStyleSelectionWidget,
)


class TableRelationPageWizard(QWizardPage):
    def __init__(
        self,
        stored_data: StoredData,
        parent=None,
    ):
        """
        QWizardPage to define table relation for a WMS-VECTOR publication

        Args:
            stored_data: stored data
            parent: parent None

        """

        super().__init__(parent)
        self.setTitle(self.tr("Créer et publier un service WMS-Vecteur"))

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "qwp_table_style_selection.ui"),
            self,
        )
        self.table_style_widgets = []

        if stored_data:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                self.clear_layout(self.lyt_table_relation)
                self.table_style_widgets = []

                for table in stored_data.get_tables():
                    wdg_table_style = TableStyleSelectionWidget(self)
                    wdg_table_style.set_table_name(table.name)
                    self.lyt_table_relation.addWidget(wdg_table_style)
                    self.table_style_widgets.append(wdg_table_style)

        self.setCommitPage(False)

    def validatePage(self) -> bool:
        """
        Validate current page content by checking files

        Returns: True

        """
        table_styles = self.get_selected_table_styles()
        if len(table_styles) == 0:
            QMessageBox.warning(
                self,
                self.tr("Aucune table sélectionnée"),
                self.tr("Veuillez choisir au moins une table."),
            )
            return False

        errors: list[str] = []
        for table_style in table_styles:
            if not table_style.stl_file:
                errors.append(
                    self.tr("Fichier de style .sld non défini pour la table {}").format(
                        table_style.native_name
                    )
                )
        if errors:
            QMessageBox.warning(
                self,
                self.tr("Champs manquants"),
                "\n".join(errors),
            )
            return False

        return True

    @staticmethod
    def clear_layout(layout):
        """Clear a layout from all added widget

        :param layout: layout to clear
        :type layout: any Qt type layouy
        """
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    layout.removeItem(item)

    def get_selected_table_styles(self) -> list[WmsVectorTableStyle]:
        """Get selected table style for WMS-Vector publish

        :return: selected table relation
        :rtype: list[WmsVectorTableStyle]
        """
        result = []
        for wdg_table_style in self.table_style_widgets:
            if table_relation := wdg_table_style.get_relation():
                result.append(table_relation)

        return result
