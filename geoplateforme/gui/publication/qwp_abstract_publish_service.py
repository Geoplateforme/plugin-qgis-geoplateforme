# standard
import os
import tempfile
from pathlib import Path
from typing import Optional

# PyQGIS
from qgis.core import QgsApplication, QgsTask
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QMessageBox, QWizardPage

# Plugin
from geoplateforme.api.datastore import DatastoreRequestManager
from geoplateforme.api.metadata import Metadata, MetadataRequestManager, MetadataType
from geoplateforme.gui.qwp_metadata_form import MetadataFormPageWizard


class AbstractPublishServicePage(QWizardPage):
    def __init__(
        self,
        qwp_metadata_form: MetadataFormPageWizard,
        datastore_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        stored_data_id: Optional[str] = None,
        parent=None,
    ):
        """QWizard page with task for metadata creation/update and publication

        :param qwp_metadata_form: page with metadata definition
        :type qwp_metadata_form: MetadataFormPageWizard
        :param datastore_id: datastore id, defaults to None
        :type datastore_id: Optional[str], optional
        :param dataset_name: dataset name, defaults to None
        :type dataset_name: Optional[str], optional
        :param stored_data_id: stored data id, defaults to None
        :type stored_data_id: Optional[str], optional
        :param parent: parent, defaults to None
        :type parent: _type_, optional
        """
        super().__init__(parent)

        self.datastore_id = datastore_id
        self.dataset_name = dataset_name
        self.stored_data_id = stored_data_id
        self.qwp_metadata_form = qwp_metadata_form

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "qwp_abstract_publish_service.ui"),
            self,
        )
        self.tbw_errors.setVisible(False)

        self.create_task = None
        self.update_task = None
        self.publish_task = None

        self.metadata_published = False
        self.publish_error = False

    def clear_errors(self) -> None:
        """Clear displayed errors"""
        self.publish_error = False
        self.lbl_result.setText("")
        self.tbw_errors.setVisible(False)

    def _add_step_in_label(self, step: str) -> None:
        """Add step in result label by getting current text and adding a new line

        :param step: step description
        :type step: str
        """
        self.lbl_result.setText(
            "\n".join(
                [
                    self.lbl_result.text(),
                    step,
                ]
            )
        )

    @staticmethod
    def _create_metadata_task(
        task: QgsTask, datastore_id: str, dataset_name: str, metadata: Metadata
    ) -> Metadata:
        """Create metadata in a QgsTask
        Create the metadata xml file and post it to geoplateforme

        :param task: task run in background
        :type task: QgsTask
        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str
        :param metadata: metadata to create
        :type metadata: Metadata
        :return: created metadata with id from geoplateforme
        :rtype: Metadata
        """
        manager = MetadataRequestManager()
        manager.update_metadata_links(metadata)
        with tempfile.TemporaryDirectory() as tmpdirname:
            temp_dir = Path(tmpdirname)
            file_name = temp_dir / f"{metadata._id}.xml"
            file_name.write_text(metadata.generate_xml_from_fields())
            metadata_type = MetadataType("ISOAP")
            metadata_open = True
            metadata = manager.create_metadata(
                datastore_id=datastore_id,
                file_path=file_name,
                open_data=metadata_open,
                metadata_type=metadata_type,
            )
            manager.add_tags(
                datastore_id, metadata._id, {"datasheet_name": dataset_name}
            )
        return metadata

    def _on_metadata_created(
        self,
        exception: Optional[Exception],
        created_metadata: Optional[Metadata] = None,
    ) -> None:
        """Callback after metadata creation.
        Check if exception was raised and launch metadata publish

        :param exception: exception raised during creation
        :type exception: Optional[Exception]
        :param created_metadata: created metadata, defaults to None
        :type created_metadata: Optional[Metadata], optional
        """
        if exception is None:
            # Update step
            self._add_step_in_label(self.tr("Métadonnée créé avec succès"))
            self._add_step_in_label(self.tr("Publication métadonnée"))

            # Publish metadata
            self.publish_task = QgsTask.fromFunction(
                "Publish metadata",
                self._publish_metadata_task,
                datastore_id=created_metadata.datastore_id,
                metadata=created_metadata,
                on_finished=self._on_metadata_published,
            )
            QgsApplication.taskManager().addTask(self.publish_task)

        else:
            self.publish_error = True
            self._add_step_in_label(
                self.tr("Erreur lors de la création de la métadonnée")
            )
            self.tbw_errors.setVisible(True)
            self.tbw_errors.setText(str(exception))

    @staticmethod
    def _update_metadata_task(
        task: QgsTask, datastore_id: str, metadata: Metadata
    ) -> Metadata:
        """Update metadata in a QgsTask
        Create the metadata xml file and post it to geoplateforme

        :param task: task run in background
        :type task: QgsTask
        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata: metadata to update
        :type metadata: Metadata
        :return: updated metadata
        :rtype: Metadata
        """
        manager = MetadataRequestManager()
        manager.update_metadata(datastore_id, metadata)
        return metadata

    def _on_metadata_updated(
        self,
        exception: Optional[Exception],
        updated_metadata: Optional[Metadata] = None,
    ) -> None:
        """Callback after metadata create or update.
        Check if exception was raised and launch metadata publish

        :param exception: exception raised during creation
        :type exception: Optional[Exception]
        :param updated_metadata: updated metadata, defaults to None
        :type updated_metadata: Optional[Metadata], optional
        """
        if exception is None:
            metadata = self.qwp_metadata_form.metadata
            if len(metadata.endpoints) == 0:
                self._add_step_in_label(self.tr("Métadonnée créée avec succès"))
                self._add_step_in_label(self.tr("Publication métadonnée"))
                self.publish_task = QgsTask.fromFunction(
                    "Publish metadata",
                    self._publish_metadata_task,
                    datastore_id=updated_metadata.datastore_id,
                    metadata=updated_metadata,
                    on_finished=self._on_metadata_published,
                )
                QgsApplication.taskManager().addTask(self.publish_task)
            else:
                self._add_step_in_label(self.tr("Metadonnee mise a jour avec succes"))
                self.metadata_published = True

        else:
            self.publish_error = True
            self._add_step_in_label(
                self.tr(
                    "Erreur lors de la création ou de la mise à jour de la métadonnée"
                )
            )
            self.tbw_errors.setVisible(True)
            self.tbw_errors.setText(str(exception))

    @staticmethod
    def _publish_metadata_task(
        task: QgsTask, datastore_id: str, metadata: Metadata
    ) -> None:
        """Publish metadata in a QgsTask

        :param task: task run in background
        :type task: QgsTask
        :param datastore_id: datastore id
        :type datastore_id: str
        :param metadata: metadata to publish
        :type metadata: Metadata
        """
        manager = MetadataRequestManager()
        # get the endpoint for the publication
        datastore_manager = DatastoreRequestManager()
        datastore = datastore_manager.get_datastore(datastore_id)
        metadata_endpoint_id = datastore.get_endpoint(data_type="METADATA")

        # publish metadata
        manager.publish(
            datastore_id=datastore_id,
            endpoint_id=metadata_endpoint_id,
            metadata_file_identifier=metadata.file_identifier,
        )
        return

    def _on_metadata_published(
        self, exception: Optional[Exception], result=None
    ) -> None:
        """Callback after metadata publication.
        Check if exception was raised and allow wizard close if succes

        :param exception: exception raised during creation
        :type exception: Optional[Exception]
        :param result: None
        :type result: None
        """
        if exception is None:
            self._add_step_in_label(self.tr("Métadonnée publiée avec succès"))
            self.metadata_published = True
        else:
            self.publish_error = True
            self._add_step_in_label(
                self.tr("Erreur lors de la publication de la métadonnée")
            )
            self.tbw_errors.setVisible(True)
            self.tbw_errors.setText(str(exception))

    def _update_metadata(self) -> None:
        """Launch steps for metadata update in QgsTask
        - metadata creation or update
        - metadata publish
        """
        metadata = self.qwp_metadata_form.metadata
        if self.qwp_metadata_form.new_metadata:
            self._add_step_in_label(self.tr("Création de la métadonnée"))
            self.create_task = QgsTask.fromFunction(
                "Create metadata",
                self._create_metadata_task,
                datastore_id=self.datastore_id,
                dataset_name=self.dataset_name,
                metadata=metadata,
                on_finished=self._on_metadata_updated,
            )
            QgsApplication.taskManager().addTask(self.create_task)
        else:
            self._add_step_in_label(self.tr("Mise à jour de la métadonnée"))
            self.update_task = QgsTask.fromFunction(
                "Update metadata",
                self._update_metadata_task,
                datastore_id=self.datastore_id,
                metadata=metadata,
                on_finished=self._on_metadata_updated,
            )
            QgsApplication.taskManager().addTask(self.update_task)

    def validatePage(self) -> bool:
        """Check if metadata was published to validate current page and avoid close of wizard

        :return: True if metadata was published or an error occurs, False otherwise
        :rtype: bool
        """

        if self.publish_error:
            return True

        if not self.metadata_published:
            QMessageBox.warning(
                self,
                self.tr("Publication métadonnée en cours."),
                self.tr(
                    "La publication de la métadonnée est en cours. Vous devez attendre la fin du traitement avant de fermer cette fenêtre."
                ),
            )
            return False
        else:
            return True
