import os
from typing import Optional

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.gui import QgsCollapsibleGroupBox, QgsExtentGroupBox
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from geoplateforme.api.metadata import Metadata, MetadataRequestManager


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
        self.le_thematics.setText(", ".join(self.metadata.fields.topics))
        self.le_inspire_kw.setText(", ".join(self.metadata.fields.inspire_keywords))
        self.le_kw.setText(", ".join(self.metadata.fields.free_keywords))

        self.le_genealogy.setText(self.metadata.fields.genealogy)
        self.de_creation_date.setDate(self.metadata.fields.creation_date)
        self.le_frequency.setText(self.metadata.fields.frequency)

        self.le_contact_email.setText(self.metadata.fields.contact_email)

        self.le_org_name.setText(self.metadata.fields.org_name)
        self.le_org_email.setText(self.metadata.fields.org_email)

        self.le_type.setText(self.metadata.fields.type)
        self.le_language.setText(self.metadata.fields.language)
        # self.le_link.setText(self.metadata.fields)
        self.le_encoding.setText(self.metadata.fields.encoding)

        if not self.creation_mode:
            self.le_unique_id.setReadOnly(True)

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
            self.gbp_capabilities.setTitle("Capabilities")
            self.gbp_capabilities.setCollapsed(True)
            self.gbp_access = QgsCollapsibleGroupBox()
            self.gbp_access.setTitle("Access")
            self.gbp_access.setCollapsed(True)
            self.gbp_style = QgsCollapsibleGroupBox()
            self.gbp_style.setTitle("Style files")
            self.gbp_style.setCollapsed(True)
            self.gbp_doc = QgsCollapsibleGroupBox()
            self.gbp_doc.setTitle("Document files")
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
            for link in self.metadata.fields.links:
                if link["type"] == "getcapabilities":
                    if first_capabilities:
                        first_capabilities = False
                    else:
                        line = QFrame()
                        line.setFrameShape(QFrame.HLine)
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
                        line.setFrameShape(QFrame.HLine)
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
                        line.setFrameShape(QFrame.HLine)
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
                        line.setFrameShape(QFrame.HLine)
                        line.setStyleSheet("color: #BBBBBB;")
                        doc_vbox.addWidget(line)
                    label_name = QLabel()
                    label_name.setText(f"<b>{link['name']}</b>")
                    doc_vbox.addWidget(label_name)
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

    def update_metadata(self):
        """Update metadata with widget fields"""
        self.metadata.fields.title = self.le_title.text()
        self.metadata.fields.abstract = self.te_description.toPlainText()
        self.le_thematics.setText(", ".join(self.metadata.fields.topics))
        self.le_inspire_kw.setText(", ".join(self.metadata.fields.inspire_keywords))
        self.le_kw.setText(", ".join(self.metadata.fields.free_keywords))

        self.metadata.fields.genealogy = self.le_genealogy.text()
        self.metadata.fields.creation_date = self.de_creation_date.date().toPyDate()
        self.metadata.fields.frequency = self.le_frequency.text()

        self.metadata.fields.contact_email = self.le_contact_email.text()

        self.metadata.fields.org_name = self.le_org_name.text()
        self.metadata.fields.org_email = self.le_org_email.text()

        self.metadata.fields.type = self.le_type.text()
        self.metadata.fields.language = self.le_language.text()
        self.metadata.fields.encoding = self.le_encoding.text()

        manager = MetadataRequestManager()
        manager.update_metadata(self.datastore_id, self.metadata)
