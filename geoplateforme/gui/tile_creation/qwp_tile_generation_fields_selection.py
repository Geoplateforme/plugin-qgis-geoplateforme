# standard
import os
from typing import Dict, List

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QMessageBox, QWizardPage

from geoplateforme.gui.mdl_table_relation import TableRelationTreeModel
from geoplateforme.gui.tile_creation.qwp_tile_generation_edition import (
    TileGenerationEditionPageWizard,
)


class TileGenerationFieldsSelectionPageWizard(QWizardPage):
    def __init__(
        self, qwp_tile_generation_edition: TileGenerationEditionPageWizard, parent=None
    ):
        """
        QWizardPage to define fields for tile generation

        Args:
            parent: parent QObject
        """

        super().__init__(parent)
        self.setTitle(self.tr("Customize your vector tiles service"))
        self.qwp_tile_generation_edition = qwp_tile_generation_edition

        uic.loadUi(
            os.path.join(
                os.path.dirname(__file__), "qwp_tile_generation_fields_selection.ui"
            ),
            self,
        )

        self.mdl_table_relation = TableRelationTreeModel(self)
        self.tw_table_relation.setModel(self.mdl_table_relation)
        self.tw_table_relation.setSortingEnabled(True)

    def initializePage(self) -> None:
        """
        Initialize page before show.

        """
        datastore_id = self.qwp_tile_generation_edition.datastore_id
        stored_data_id = self.qwp_tile_generation_edition.stored_data_id

        self.mdl_table_relation.set_stored_data(datastore_id, stored_data_id)

    def get_selected_attributes(self) -> Dict[str, List[str]]:
        """
        Get list of selected attributes

        Returns: {str:[str]} map of selected attributes for each table

        """
        attributes = {}
        tables_attributes = self.mdl_table_relation.get_selected_table_attributes()
        for table, table_attributes in tables_attributes.items():
            if len(table_attributes) != 0:
                attributes[table] = table_attributes
        return attributes

    def validatePage(self) -> bool:
        """
        Validate current page content by checking files

        Returns: True

        """
        valid = True
        selected_attributes = self.get_selected_attributes()

        if len(selected_attributes) == 0:
            valid = False
            QMessageBox.warning(
                self,
                self.tr("No table selected."),
                self.tr("Please select one or more tables."),
            )

        for key, val in selected_attributes.items():
            if len(val) == 0:
                valid = False
                QMessageBox.warning(
                    self,
                    self.tr("No attribute selected."),
                    self.tr(f"Please select one or more attributes for table {key}."),
                )

        return valid
