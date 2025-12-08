import os
from typing import Optional

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.gui import QgsCollapsibleGroupBox, QgsExtentGroupBox
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QCompleter, QFrame, QLabel, QVBoxLayout, QWidget

from geoplateforme.api.metadata import Metadata, MetadataRequestManager
from geoplateforme.constants import (
    metadata_encoding_values,
    metadata_inspire_keyword,
    metadata_languages,
    metadata_maintenance_frequency,
    metadata_topic_categories,
)
from geoplateforme.gui.metadata.wdg_tagbar import DictTagBarWidget, ListTagBarWidget


class MetadataDetailsWidget(QWidget):
    def __init__(
        self,
        metadata: Optional[Metadata],
        datastore_id: Optional[str],
        creation_mode: bool = False,
    ):
        """QWidget to display metadata details

        :param metadata: Metadata to dispaly
        :type metadata: Metadata
        :param datastore_id: datastore id
        :type datastore_id: str
        :param detailed: display all fields, defaults to False
        :type detailed: bool, optional
        """
        super().__init__()

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_metadata_details.ui"),
            self,
        )
        self.creation_mode = creation_mode
        self.metadata = metadata
        self.datastore_id = datastore_id

        if self.metadata is not None and datastore_id is not None:
            self.initFields()

    def setMetadata(self, metadata: Metadata, datastore_id: str):
        """
        Set metadata and datastore id

        :param metadata: the metadata
        :type metadata: Metadata
        :param datastore_id: datastore id
        :type datastore_id: str
        """
        self.metadata = metadata
        self.datastore_id = datastore_id

    def initFields(self):
        """Fill widget with metadata"""
        self.le_title.setText(self.metadata.fields.title)
        self.te_description.setText(self.metadata.fields.abstract)
        self.le_context.setText(self.datastore_id)
        self.le_unique_id.setText(self.metadata.fields.identifier)
        self.tb_thematics = DictTagBarWidget(metadata_topic_categories)
        self.gl_description.addWidget(self.tb_thematics, 4, 2)
        if self.metadata.fields.topics:
            self.tb_thematics.create_tags(self.metadata.fields.topics)
        self.tb_inspire_kw = ListTagBarWidget(metadata_inspire_keyword)
        self.gl_description.addWidget(self.tb_inspire_kw, 5, 2)
        if self.metadata.fields.inspire_keywords:
            self.tb_inspire_kw.create_tags(self.metadata.fields.inspire_keywords)
        if self.metadata.fields.free_keywords:
            self.le_kw.setText(", ".join(self.metadata.fields.free_keywords))

        self.le_genealogy.setText(self.metadata.fields.genealogy)
        if self.metadata.fields.creation_date:
            self.de_creation_date.setDate(self.metadata.fields.creation_date)
        self.cb_frequency.addItems([v for v in metadata_maintenance_frequency.values()])
        self.cb_frequency.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.cb_frequency.setCurrentText("Inconnue")
        if (
            self.metadata.fields.frequency
            and self.metadata.fields.frequency in metadata_maintenance_frequency
        ):
            self.cb_frequency.setCurrentText(
                metadata_maintenance_frequency[self.metadata.fields.frequency]
            )

        self.le_contact_email.setText(self.metadata.fields.contact_email)

        self.le_org_name.setText(self.metadata.fields.org_name)
        self.le_org_email.setText(self.metadata.fields.org_email)

        self.cb_type.addItems(["dataset", "series"])
        self.cb_type.setCurrentText("dataset")
        if self.metadata.fields.type and self.metadata.fields.type in [
            "dataset",
            "series",
        ]:
            self.cb_type.setCurrentText(self.metadata.fields.type)

        self.cb_language.addItems([v for v in metadata_languages.values()])
        self.cb_language.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.cb_language.setCurrentText("français")
        if (
            self.metadata.fields.language
            and self.metadata.fields.language in metadata_languages
        ):
            self.cb_language.setCurrentText(
                metadata_languages[self.metadata.fields.language]
            )

        self.cb_encoding.addItems(metadata_encoding_values)
        self.cb_encoding.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.cb_encoding.setCurrentText("utf8")
        if (
            self.metadata.fields.encoding
            and self.metadata.fields.encoding in metadata_encoding_values
        ):
            self.cb_encoding.setCurrentText(self.metadata.fields.encoding)

        if self.creation_mode:
            self.lbl_link.hide()
            self.le_link.hide()
        else:
            self.le_unique_id.setReadOnly(True)

            self.lbl_link.show()
            self.le_link.show()
            self.le_link.setReadOnly(True)
            self.le_link.setText(self.metadata.url)

            self.gbp_bbox = QgsExtentGroupBox()
            self.gbp_bbox.setTitle("Bounding Box")
            if self.metadata.fields.bbox is not None:
                extent = QgsRectangle(
                    self.metadata.fields.bbox["xmin"],
                    self.metadata.fields.bbox["ymin"],
                    self.metadata.fields.bbox["xmax"],
                    self.metadata.fields.bbox["ymax"],
                )
                self.gbp_bbox.setOriginalExtent(
                    extent, QgsCoordinateReferenceSystem("EPSG:4326")
                )
                self.gbp_bbox.setOutputExtentFromOriginal()
            self.gbp_bbox.setCollapsed(True)
            self.scrollAreaWidgetContents.layout().insertWidget(1, self.gbp_bbox)

            self.gbp_capabilities = QgsCollapsibleGroupBox()
            self.gbp_capabilities.setTitle(self.tr("Capabilities"))
            self.gbp_capabilities.setCollapsed(True)
            self.gbp_access = QgsCollapsibleGroupBox()
            self.gbp_access.setTitle(self.tr("Access"))
            self.gbp_access.setCollapsed(True)
            self.gbp_style = QgsCollapsibleGroupBox()
            self.gbp_style.setTitle(self.tr("Style files"))
            self.gbp_style.setCollapsed(True)
            self.gbp_doc = QgsCollapsibleGroupBox()
            self.gbp_doc.setTitle(self.tr("Document files"))
            self.gbp_doc.setCollapsed(True)
            capabilities_vbox = QVBoxLayout()
            self.gbp_capabilities.setLayout(capabilities_vbox)
            access_vbox = QVBoxLayout()
            self.gbp_access.setLayout(access_vbox)
            style_vbox = QVBoxLayout()
            self.gbp_style.setLayout(style_vbox)
            doc_vbox = QVBoxLayout()
            self.gbp_doc.setLayout(doc_vbox)
            first_capabilities = True
            first_access = True
            if self.metadata.fields.links is not None:
                for link in self.metadata.fields.links:
                    if link["type"] == "getcapabilities":
                        if first_capabilities:
                            first_capabilities = False
                        else:
                            line = QFrame()
                            line.setFrameShape(QFrame.Shape.HLine)
                            line.setStyleSheet("color: #BBBBBB;")
                            capabilities_vbox.addWidget(line)
                        label_name = QLabel()
                        label_name.setText(f"<b>{link['name']}</b>")
                        capabilities_vbox.addWidget(label_name)
                        label_description = QLabel()
                        label_description.setText(
                            f"<b>Description :</b> {link['description']}"
                        )
                        capabilities_vbox.addWidget(label_description)
                        label_url = QLabel()
                        label_url.setText(f"<b>URL :</b> {link['url']}")
                        capabilities_vbox.addWidget(label_url)
                    if link["type"] == "offering":
                        if first_access:
                            first_access = False
                        else:
                            line = QFrame()
                            line.setFrameShape(QFrame.Shape.HLine)
                            line.setStyleSheet("color: #BBBBBB;")
                            access_vbox.addWidget(line)
                        label_name = QLabel()
                        label_name.setText(f"<b>{link['name']}</b>")
                        access_vbox.addWidget(label_name)
                        label_description = QLabel()
                        label_description.setText(f"<b>Type :</b> {link['format']}")
                        access_vbox.addWidget(label_description)
                        label_url = QLabel()
                        label_url.setText(f"<b>URL :</b> {link['url']}")
                        access_vbox.addWidget(label_url)
                    if link["type"] == "style":
                        if first_access:
                            first_access = False
                        else:
                            line = QFrame()
                            line.setFrameShape(QFrame.Shape.HLine)
                            line.setStyleSheet("color: #BBBBBB;")
                            style_vbox.addWidget(line)
                        label_name = QLabel()
                        label_name.setText(f"<b>{link['name']}</b>")
                        style_vbox.addWidget(label_name)
                        label_url = QLabel()
                        label_url.setText(f"<b>URL :</b> {link['url']}")
                        style_vbox.addWidget(label_url)
                    if link["type"] == "document":
                        if first_access:
                            first_access = False
                        else:
                            line = QFrame()
                            line.setFrameShape(QFrame.Shape.HLine)
                            line.setStyleSheet("color: #BBBBBB;")
                            doc_vbox.addWidget(line)
                        label_name = QLabel()
                        label_name.setText(f"<b>{link['name']}</b>")
                        doc_vbox.addWidget(label_name)
                        if "description" in link:
                            label_description = QLabel()
                            label_description.setText(
                                f"<b>Description :</b> {link['description']}"
                            )
                            doc_vbox.addWidget(label_description)
                        label_url = QLabel()
                        label_url.setText(f"<b>URL :</b> {link['url']}")
                        doc_vbox.addWidget(label_url)
            self.scrollAreaWidgetContents.layout().insertWidget(6, self.gbp_access)
            self.scrollAreaWidgetContents.layout().insertWidget(7, self.gbp_style)
            self.scrollAreaWidgetContents.layout().insertWidget(
                8, self.gbp_capabilities
            )
            self.scrollAreaWidgetContents.layout().insertWidget(9, self.gbp_doc)
        self.update()

    def update_metadata_fields(self):
        """Update metadata with widget fields"""
        self.metadata.fields.title = self.le_title.text()
        self.metadata.fields.abstract = self.te_description.toPlainText()
        self.metadata.fields.identifier = self.le_unique_id.text()
        if len(self.tb_thematics.tags) > 0:
            self.metadata.fields.topics = self.tb_thematics.tags
        else:
            self.metadata.fields.topics = []
        if len(self.tb_inspire_kw.tags) > 0:
            self.metadata.fields.inspire_keywords = self.tb_inspire_kw.tags
        else:
            self.metadata.fields.inspire_keywords = []

        if self.le_kw.text():
            self.metadata.fields.free_keywords = self.le_kw.text().split(",")
        else:
            self.metadata.fields.free_keywords = []

        self.metadata.fields.genealogy = self.le_genealogy.text()
        if not self.de_creation_date.date().isNull():
            self.metadata.fields.creation_date = self.de_creation_date.date().toPyDate()
        self.metadata.fields.frequency = list(metadata_maintenance_frequency.keys())[
            list(metadata_maintenance_frequency.values()).index(
                self.cb_frequency.currentText()
            )
        ]

        self.metadata.fields.contact_email = self.le_contact_email.text()

        self.metadata.fields.org_name = self.le_org_name.text()
        self.metadata.fields.org_email = self.le_org_email.text()

        self.metadata.fields.type = self.cb_type.currentText()
        self.metadata.fields.language = list(metadata_languages.keys())[
            list(metadata_languages.values()).index(self.cb_language.currentText())
        ]
        self.metadata.fields.encoding = self.cb_encoding.currentText()

    def update_metadata(self):
        """Update metadata on GPF with widget fields"""
        self.update_metadata_fields()
        manager = MetadataRequestManager()
        manager.update_metadata(self.datastore_id, self.metadata, True)
