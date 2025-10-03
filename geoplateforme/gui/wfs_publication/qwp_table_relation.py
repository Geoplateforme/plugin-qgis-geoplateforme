# standard
import os
from typing import Optional

# PyQGIS
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QWizardPage
from qgis.utils import OverrideCursor

from geoplateforme.api.configuration import WfsRelation
from geoplateforme.api.stored_data import StoredData
from geoplateforme.gui.wfs_publication.wdg_table_relation import TableRelationWidget


class TableRelationPageWizard(QWizardPage):
    def __init__(
        self,
        parent=None,
        datastore_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        stored_data: Optional[StoredData] = None,
    ):
        """
        QWizardPage to define table relation for a WFS publication

        Args:
            parent: parent None
            datastore_id: datastore id
            dataset_name: dataset name
            stored_data_id: store data id

        """

        super().__init__(parent)
        self.setTitle(self.tr("Créer et publier un service WFS"))

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "qwp_table_relation.ui"), self
        )
        self.table_relation_widgets = []
        self.datastore_id = datastore_id
        self.dataset_name = dataset_name
        self.stored_data_id = None

        if stored_data:
            self.stored_data_id = stored_data._id
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                self.clear_layout(self.lyt_table_relation)
                self.table_relation_widgets = []

                for table in stored_data.get_tables():
                    wdg_table_relation = TableRelationWidget(self)
                    wdg_table_relation.set_table_name(table.name)
                    self.lyt_table_relation.addWidget(wdg_table_relation)
                    self.table_relation_widgets.append(wdg_table_relation)

        self.setCommitPage(False)

    def validatePage(self) -> bool:
        """
        Validate current page content by checking files

        Returns: True

        """
        table_relations = self.get_selected_table_relations()
        if len(table_relations) == 0:
            QMessageBox.warning(
                self,
                self.tr("Aucune table sélectionnée"),
                self.tr("Veuillez choisir au moins une table."),
            )
            return False

        errors: list[str] = []
        for table_relation in table_relations:
            if not table_relation.title:
                errors.append(
                    self.tr("Titre manquant pour la table {}").format(
                        table_relation.native_name
                    )
                )
            if not table_relation.abstract:
                errors.append(
                    self.tr("Description manquante pour la table {}").format(
                        table_relation.native_name
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

    def get_selected_table_relations(self) -> list[WfsRelation]:
        """Get selected table relation for WFS publish

        :return: selected table relation
        :rtype: list[WfsRelation]
        """
        result = []
        for wdg_table_relation in self.table_relation_widgets:
            if table_relation := wdg_table_relation.get_relation():
                result.append(table_relation)

        return result
