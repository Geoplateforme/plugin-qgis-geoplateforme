import os
import webbrowser
from time import sleep
from typing import Dict, List, Optional

# PyQGIS
from qgis.core import QgsApplication, QgsTask
from qgis.PyQt import QtCore, uic
from qgis.PyQt.QtCore import (
    QAbstractItemModel,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    Qt,
)
from qgis.PyQt.QtGui import QCursor, QGuiApplication, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableView,
    QWidget,
)
from qgis.utils import OverrideCursor

from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.configuration import ConfigurationRequestManager
from geoplateforme.api.custom_exceptions import (
    DeleteMetadataException,
    ReadConfigurationException,
    ReadMetadataException,
    ReadOfferingException,
    ReadStoredDataException,
    ReadUploadException,
    UnavailableMetadataFileException,
)
from geoplateforme.api.metadata import Metadata, MetadataRequestManager
from geoplateforme.api.offerings import Offering, OfferingsRequestManager
from geoplateforme.api.stored_data import (
    StoredData,
    StoredDataRequestManager,
    StoredDataStatus,
    StoredDataStep,
    StoredDataType,
)
from geoplateforme.api.upload import Upload, UploadRequestManager
from geoplateforme.constants import cartes_gouv_template_url
from geoplateforme.gui.dashboard.dlg_stored_data_details import StoredDataDetailsDialog
from geoplateforme.gui.dashboard.wdg_service_details import ServiceDetailsWidget
from geoplateforme.gui.dashboard.wdg_upload_details import UploadDetailsWidget
from geoplateforme.gui.mdl_document import DocumentListModel
from geoplateforme.gui.mdl_offering import OfferingListModel
from geoplateforme.gui.mdl_stored_data import StoredDataListModel
from geoplateforme.gui.mdl_upload import UploadListModel
from geoplateforme.gui.metadata.wdg_metadata_details import MetadataDetailsWidget
from geoplateforme.gui.proxy_model_stored_data import StoredDataProxyModel
from geoplateforme.gui.upload_creation.wzd_upload_creation import UploadCreationWizard
from geoplateforme.processing.provider import GeoplateformeProvider
from geoplateforme.processing.tools.delete_offering import DeleteOfferingAlgorithm
from geoplateforme.processing.tools.delete_stored_data import DeleteStoredDataAlgorithm
from geoplateforme.processing.tools.delete_upload import DeleteUploadAlgorithm
from geoplateforme.toolbelt import PlgLogger
from geoplateforme.toolbelt.dlg_processing_run import ProcessingRunDialog
from geoplateforme.toolbelt.preferences import PlgOptionsManager


class DashboardWidget(QWidget):
    def __init__(self, parent: QWidget = None):
        """
        QWidget to display dashboard

        Args:
            parent: parent QWidget
        """
        super().__init__(parent)
        self.log = PlgLogger().log

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "wdg_dashboard.ui"),
            self,
        )

        # Task for API call in background
        self.update_metadata_task = None
        self.refresh_task = None

        # Flag to define if a refresh is in progress
        self.refresh_in_progress = False

        # Add metadata widget
        self.wdg_metadata = None
        self._set_metadata_view()

        # Create model for upload display
        self.mdl_upload = UploadListModel(self)

        # Create model for stored data display
        self.mdl_stored_data = StoredDataListModel(self)

        # Create model for offering display
        self.mdl_offering = OfferingListModel(self)

        # Create model for document display
        self.mdl_document = DocumentListModel(self)

        # List of table view
        self.tbv_list = []

        # Initialize upload table view
        self.tbv_upload.setModel(self.mdl_upload)
        self.tbv_upload.verticalHeader().setVisible(False)
        self.tbv_upload.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.tbv_upload.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_list.append(self.tbv_upload)
        self.tbv_upload.selectionModel().selectionChanged.connect(
            lambda selection: self._item_selection_changed(
                selection, self.mdl_upload, self.tbv_upload
            )
        )

        # Create proxy model for each table
        # Vector DB
        self._init_table_view(
            tbv=self.tbv_vector_db,
            filter_type=[StoredDataType.VECTORDB],
            visible_steps=[],
            visible_status=[],
        )
        self.tbv_list.append(self.tbv_vector_db)

        # Pyramids vector
        self._init_table_view(
            tbv=self.tbv_pyramid_vector,
            filter_type=[StoredDataType.PYRAMIDVECTOR],
            visible_steps=[],
            visible_status=[],
        )
        self.tbv_list.append(self.tbv_pyramid_vector)

        # Pyramids raster
        self._init_table_view(
            tbv=self.tbv_pyramid_raster,
            filter_type=[StoredDataType.PYRAMIDRASTER],
            visible_steps=[],
            visible_status=[],
        )
        self.tbv_list.append(self.tbv_pyramid_raster)

        # Initialize service table view
        self.tbv_service.setModel(self.mdl_offering)
        self.tbv_service.verticalHeader().setVisible(False)
        self.tbv_service.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.tbv_service.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.tbv_service.pressed.connect(self._service_clicked)
        self.tbv_service.selectionModel().selectionChanged.connect(
            self._service_selection_changed
        )

        # Initialize document table view
        self.tbv_document.setModel(self.mdl_document)
        self.tbv_document.verticalHeader().setVisible(False)
        self.tbv_document.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tbv_document.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tbv_document.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.tbv_document.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbv_document.doubleClicked.connect(self._document_clicked)

        self.btn_document.clicked.connect(self._open_document_url)

        # remove detail zone
        self.detail_dialog = None
        self.remove_detail_zone()

        self.service_detail_dialog = None
        self.remove_service_detail_zone()

        self.import_wizard = None

        self.cbx_datastore.currentIndexChanged.connect(self._on_datastore_updated)
        self.cbx_dataset.activated.connect(self._on_dataset_updated)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_refresh.setIcon(QIcon(":/images/themes/default/mActionRefresh.svg"))

        self.btn_delete_dataset.clicked.connect(self.delete_dataset)
        self.btn_delete_dataset.setIcon(
            QIcon(str(DIR_PLUGIN_ROOT / "resources/images/icons/Supprimer.svg"))
        )

        self.btn_create.clicked.connect(self._create_dataset)
        self.btn_create.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))

        self.btn_add_data.clicked.connect(self._add_data_to_dataset)
        self.btn_add_data.setIcon(QIcon(":/images/themes/default/mActionAdd.svg"))

    def _open_document_url(self) -> None:
        """Open document URL on webbrowser"""
        datastore_id = self.cbx_datastore.current_datastore_id()
        dataset_name = self.cbx_dataset.current_dataset_name()
        documents_url = (
            PlgOptionsManager.get_plg_settings().url_geoplateforme.rstrip("/")
            + cartes_gouv_template_url["document"]
        )
        documents_url = documents_url.replace("{datastore_id}", datastore_id)
        documents_url = documents_url.replace("{dataset_name}", dataset_name)
        webbrowser.open(documents_url)

    def _document_clicked(self, index: QModelIndex) -> None:
        document = self.mdl_document.data(
            self.mdl_document.index(index.row(), 0), Qt.ItemDataRole.UserRole
        )
        if document:
            webbrowser.open(document["url"])

    def _init_table_view(
        self,
        tbv: QTableView,
        filter_type: List[StoredDataType],
        visible_steps: List[StoredDataStep],
        visible_status: List[StoredDataStatus],
    ) -> None:
        """
        Initialization of a table view for specific stored data steps and status visibility

        Args:
            tbv:  QTableView table view
            filter_type: List[StoredDataType] visible types
            visible_steps: List[StoredDataStep] visible stored data steps
            visible_status: List[StoredDataStatus] visible stored data status
        """
        proxy_mdl = self._create_proxy_model(
            filter_type=filter_type,
            visible_steps=visible_steps,
            visible_status=visible_status,
        )
        tbv.setModel(proxy_mdl)
        tbv.verticalHeader().setVisible(False)
        tbv.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbv.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbv.selectionModel().selectionChanged.connect(
            lambda selection: self._item_selection_changed(selection, proxy_mdl, tbv)
        )

    def _set_metadata_view(self) -> None:
        """
        Create metadata view when metadata is present
        """
        if self.wdg_metadata is not None:
            if isinstance(self.wdg_metadata, MetadataDetailsWidget):
                self.btn_update_metadata.clicked.disconnect(self._run_metadata_update)
            self.metadata_layout.removeWidget(self.wdg_metadata)
            self.wdg_metadata = None

        datastore_id = self.cbx_datastore.current_datastore_id()
        dataset_name = self.cbx_dataset.current_dataset_name()

        metadatas = []
        manager = MetadataRequestManager()
        if datastore_id and dataset_name:
            tags = {"datasheet_name": dataset_name}
            metadatas = manager._get_metadata_list(datastore_id=datastore_id, tags=tags)
        metadata = None
        if len(metadatas) == 1:
            try:
                metadata = metadatas[0]
                self.wdg_metadata = MetadataDetailsWidget(
                    metadata=metadata, datastore_id=datastore_id
                )
                self.btn_update_metadata.clicked.connect(self._run_metadata_update)
                self.btn_update_metadata.show()
            except UnavailableMetadataFileException as exc:
                self.log(
                    f"Error while getting Metadata informations: {exc}",
                    log_level=2,
                    push=False,
                )
            except ReadMetadataException as exc:
                self.log(
                    f"Error while reading Metadata informations: {exc}",
                    log_level=2,
                    push=False,
                )
        if metadata is None:
            self.wdg_metadata = QLabel()
            self.wdg_metadata.setText("No metadata available")
            self.btn_update_metadata.hide()
        self.metadata_layout.addWidget(self.wdg_metadata)

    def _update_metadata(self, task: QgsTask):
        """Update metadata"""
        if self.wdg_metadata is not None:
            self.wdg_metadata.update_metadata()

    def _run_metadata_update(self) -> None:
        """Run metadata update in a QgsTask
        Widget is disabled during update
        """
        self.setEnabled(False)
        self.update_metadata_task = QgsTask.fromFunction(
            "Update metadata",
            self._update_metadata,
            on_finished=self._on_metadata_updated,
            flags=QgsTask.Flag.Hidden | QgsTask.Flag.Silent,
        )
        QgsApplication.taskManager().addTask(self.update_metadata_task)

    def _on_metadata_updated(self, exception, value=None) -> None:
        """Enable widget after a metadata update.
        Display any raised exception.

        :param exception: _description_
        :type exception: _type_
        :param value: _description_, defaults to None
        :type value: _type_, optional
        """
        if exception:
            QMessageBox.warning(
                self,
                self.tr("Erreur mise à jour métadonnée."),
                self.tr(f"Erreur lors de la mise à jour des métadonnée. : {exception}"),
            )
        self.setEnabled(True)

    def delete_dataset(
        self, datastore_id: Optional[str] = None, dataset_name: Optional[str] = None
    ) -> None:
        """Delete dataset by removing all related element from geoplateforme:
        - offering and configuration
        - stored data
        - upload
        - metadata

        :param datastore_id: datastore id, defaults to None, use current selected datastore
        :type datastore_id: Optional[str], optional
        :param dataset_name: dataset_name, defaults to None, use current selected dataset
        :type dataset_name: Optional[str], optional
        """
        if not datastore_id:
            datastore_id = self.cbx_datastore.current_datastore_id()
        if not dataset_name:
            dataset_name = self.cbx_dataset.current_dataset_name()

        if not dataset_name or not datastore_id:
            QMessageBox.warning(
                self,
                self.tr("Suppression impossible"),
                self.tr("L'entrepôt ou le dataset ne sont pas définis"),
            )
            return

        # Get all data related to dataset
        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                # Offering
                offering_list = self._get_dataset_offering(
                    datastore_id=datastore_id, dataset_name=dataset_name
                )
                # Stored data
                stored_data_list = self._get_dataset_stored_data(
                    datastore_id=datastore_id, dataset_name=dataset_name
                )
                # Upload
                upload_list = self._get_dataset_upload(
                    datastore_id=datastore_id, dataset_name=dataset_name
                )
                # Metadata
                metadata_list = self._get_dataset_metadata(
                    datastore_id=datastore_id, dataset_name=dataset_name
                )
        except (ReadConfigurationException, ReadOfferingException) as exc:
            QMessageBox.critical(
                self,
                self.tr("Suppression impossible"),
                self.tr(
                    "Impossible de récupérer les configurations et offres associées au dataset : {}".format(
                        exc
                    )
                ),
            )
            return
        except ReadStoredDataException as exc:
            QMessageBox.critical(
                self,
                self.tr("Suppression impossible"),
                self.tr(
                    "Impossible de récupérer les données stockées associées au dataset : {}".format(
                        exc
                    )
                ),
            )
            return
        except ReadUploadException as exc:
            QMessageBox.critical(
                self,
                self.tr("Suppression impossible"),
                self.tr(
                    "Impossible de récupérer les livraisons associées au dataset : {}".format(
                        exc
                    )
                ),
            )
            return
        except ReadMetadataException as exc:
            QMessageBox.critical(
                self,
                self.tr("Suppression impossible"),
                self.tr(
                    "Impossible de récupérer les métadatas associées au dataset : {}".format(
                        exc
                    )
                ),
            )
            return

        # Indicate to user number of deleted elements
        message = self.tr("Êtes-vous sûr de vouloir supprimer le dataset ?")
        message += self.tr("\nLes éléments suivants seront supprimés:")
        # Offering
        nb_offer = len(offering_list)
        if nb_offer != 0:
            message += self.tr("\n{} Offre(s)".format(nb_offer))
        # Stored data
        nb_stored_data = len(stored_data_list)
        if nb_stored_data != 0:
            message += self.tr("\n{} Données stockées(s)".format(nb_stored_data))
        # Upload
        nb_upload = len(upload_list)
        if nb_upload != 0:
            message += self.tr("\n{} Livraison(s)".format(nb_upload))
        # Metadata
        nb_metadata = len(metadata_list)
        if nb_metadata != 0:
            message += self.tr(
                "\n La métadonnée associée ({})".format(
                    metadata_list[0].file_identifier
                )
            )

        reply = QMessageBox.question(
            self,
            self.tr("Suppression dataset {}".format(dataset_name)),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            # Delete offering
            if not self._delete_dataset_offering(offering_list=offering_list):
                return

            # Delete stored data
            if not self._delete_dataset_stored_data(stored_data_list=stored_data_list):
                return

            # Delete upload
            if not self._delete_dataset_upload(upload_list=upload_list):
                return

            # Delete metadata
            if not self._delete_dataset_metadata(metadata_list=metadata_list):
                return

        self.refresh()

    def _get_dataset_offering(
        self, datastore_id: str, dataset_name: str
    ) -> List[Offering]:
        """Get list of offering for a dataset

        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str
        :return: list of offering related to a dataset
        :rtype: List[Offering]
        """
        result = []
        config_manager = ConfigurationRequestManager()
        offerring_manager = OfferingsRequestManager()

        # Get all configuration for dataset
        tags = {"datasheet_name": dataset_name}
        configurations = config_manager.get_configuration_list(
            datastore_id=datastore_id,
            tags=tags,
        )

        # Get offering for each configuration
        for config in configurations:
            offering_list = offerring_manager.get_offering_list(
                datastore_id=config.datastore_id,
                configuration_id=config._id,
            )

            result.extend(offering_list)

        return result

    def _delete_dataset_offering(self, offering_list: List[Offering]) -> bool:
        """Delete a list of offering for a dataset
        Display message box in case of errors.

        :param offering_list: offering to delete
        :type offering_list: List[Offering]
        :return: True if no error occured, False otherwise
        :rtype: bool
        """
        # Delete offering
        offering_list_by_datastore: Dict[str, List[str]] = {}
        for offering in offering_list:
            if offering.datastore_id in offering_list_by_datastore:
                offering_list_by_datastore[offering.datastore_id].append(offering._id)
            else:
                offering_list_by_datastore[offering.datastore_id] = [offering._id]

        for datastore_id, offerring_ids in offering_list_by_datastore.items():
            params = {
                DeleteOfferingAlgorithm.DATASTORE: datastore_id,
                DeleteOfferingAlgorithm.OFFERING: ",".join(offerring_ids),
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteOfferingAlgorithm().name()}"
            )
            run_dialog = ProcessingRunDialog(
                alg_name=algo_str,
                params=params,
                title=self.tr("Unpublish services"),
                parent=self,
            )
            run_dialog.exec()
            success, _ = run_dialog.processing_results()
            if not success:
                QMessageBox.critical(
                    self,
                    self.tr("Suppression impossible"),
                    self.tr("Un service n'a pas pu être dépublié :\n {}").format(
                        run_dialog.get_feedback().textLog()
                    ),
                )
                return False

        return True

    def _get_dataset_stored_data(
        self, datastore_id: str, dataset_name: str
    ) -> List[StoredData]:
        """Get list of stored data for a dataset

        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str
        :return: list of stored data related to a dataset
        :rtype: List[StoredData]
        """
        manager = StoredDataRequestManager()

        # Get all stored data for dataset
        tags = {"datasheet_name": dataset_name}
        stored_data_list = manager.get_stored_data_list(
            datastore_id=datastore_id,
            tags=tags,
        )
        return stored_data_list

    def _delete_dataset_stored_data(self, stored_data_list: List[StoredData]) -> bool:
        """Delete a list of stored data for a dataset
        Display message box in case of errors.

        :param stored_data_list: stored data to delete
        :type stored_data_list: List[StoredData]
        :return: True if no error occured, False otherwise
        :rtype: bool
        """
        # Delete stored data
        for stored_data in stored_data_list:
            params = {
                DeleteStoredDataAlgorithm.DATASTORE: stored_data.datastore_id,
                DeleteStoredDataAlgorithm.STORED_DATA: stored_data._id,
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteStoredDataAlgorithm().name()}"
            )
            run_dialog = ProcessingRunDialog(
                alg_name=algo_str,
                params=params,
                title=self.tr("Delete stored data {}").format(stored_data.name),
                parent=self,
            )
            run_dialog.exec()
            success, _ = run_dialog.processing_results()
            if not success:
                QMessageBox.critical(
                    self,
                    self.tr("Suppression impossible"),
                    self.tr(
                        "Une données stockées n'a pas pu être supprimée :\n {}"
                    ).format(run_dialog.get_feedback().textLog()),
                )
                return False
        return True

    def _get_dataset_upload(self, datastore_id: str, dataset_name: str) -> List[Upload]:
        """Get list of upload for a dataset

        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str
        :return: list of upload related to a dataset
        :rtype: List[Upload]
        """
        manager = UploadRequestManager()

        # Get all upload for dataset
        tags = {"datasheet_name": dataset_name}
        upload_list = manager.get_upload_list(
            datastore_id=datastore_id,
            tags=tags,
        )
        return upload_list

    def _delete_dataset_upload(self, upload_list: List[Upload]) -> bool:
        """Delete a list of upload for a dataset
        Display message box in case of errors.

        :param upload_list: upload to delete
        :type upload_list: List[Upload]
        :return: True if no error occured, False otherwise
        :rtype: bool
        """
        # Delete upload
        for upload in upload_list:
            params = {
                DeleteUploadAlgorithm.DATASTORE: upload.datastore_id,
                DeleteUploadAlgorithm.UPLOAD: upload._id,
            }

            algo_str = (
                f"{GeoplateformeProvider().id()}:{DeleteUploadAlgorithm().name()}"
            )
            run_dialog = ProcessingRunDialog(
                alg_name=algo_str,
                params=params,
                title=self.tr("Delete upload {}").format(upload.name),
                parent=self,
            )
            run_dialog.exec()
            success, _ = run_dialog.processing_results()
            if not success:
                QMessageBox.critical(
                    self,
                    self.tr("Suppression impossible"),
                    self.tr("Une livraison n'a pas pu être supprimée :\n {}").format(
                        run_dialog.get_feedback().textLog()
                    ),
                )
                return False
        return True

    def _get_dataset_metadata(
        self, datastore_id: str, dataset_name: str
    ) -> List[Metadata]:
        """Get list of metadata for a dataset

        :param datastore_id: datastore id
        :type datastore_id: str
        :param dataset_name: dataset name
        :type dataset_name: str
        :return: list of metadata related to a dataset
        :rtype: List[Metadata]
        """
        manager = MetadataRequestManager()

        # Get all metadata for dataset
        tags = {"datasheet_name": dataset_name}
        metadata_list = manager.get_metadata_list(
            datastore_id=datastore_id,
            tags=tags,
        )
        return metadata_list

    def _delete_dataset_metadata(self, metadata_list: List[Metadata]) -> bool:
        """Delete a list of metadata for a dataset
        Display message box in case of errors.

        :param metadata_list: metadata to delete
        :type metadata_list: List[Metadata]
        :return: True if no error occured, False otherwise
        :rtype: bool
        """
        manager = MetadataRequestManager()

        # Delete metadata
        for metadata in metadata_list:
            try:
                manager.delete(
                    datastore_id=metadata.datastore_id, metadata_id=metadata._id
                )
            except DeleteMetadataException as exc:
                QMessageBox.critical(
                    self,
                    self.tr("Suppression impossible"),
                    self.tr("Une metadata n'a pas pu être supprimée : {}".format(exc)),
                )
                return False
        return True

    def _refresh_task(
        self,
        task: QgsTask,
        datastore_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        force_refresh: bool = False,
    ) -> None:
        """
        Function run as QgsTask to refresh dashboard.
        Warning : No change of QWidget parent can't be done inside this function.
        Only table and combobox models can be updated with Geoplateforme API result

        :param task: task used for function (unused but mandatory for QGIS)
        :type task: QgsTask
        :param datastore_id: datastore id to use, defaults to None (use current datastore id)
        :type datastore_id: Optional[str], optional
        :param dataset_name: dataset name to use, defaults to None (use current dataset name)
        :type dataset_name: Optional[str], optional
        :param force_refresh: force refresh of datastore and dataset models, defaults to False
        :type force_refresh: bool, optional
        """
        if not datastore_id:
            datastore_id = self.cbx_datastore.current_datastore_id()
        if not dataset_name:
            dataset_name = self.cbx_dataset.current_dataset_name()

        # Try to disconnect signals
        try:
            self.cbx_datastore.currentIndexChanged.disconnect(
                self._on_datastore_updated
            )
            self.cbx_dataset.activated.disconnect(self._on_dataset_updated)
        except (TypeError, RuntimeError):
            pass

        # Update datastore content
        if force_refresh:
            self.cbx_datastore.refresh()
        self.cbx_datastore.set_datastore_id(datastore_id)

        # Update dataset
        self.cbx_dataset.set_datastore_id(datastore_id, force_refresh)
        self.cbx_dataset.set_dataset_name(dataset_name)

        # Connect signals
        self.cbx_datastore.currentIndexChanged.connect(self._on_datastore_updated)
        self.cbx_dataset.activated.connect(self._on_dataset_updated)

        # Update dataset table
        self._update_dataset_table()

    def refresh(
        self,
        datastore_id: Optional[str] = None,
        dataset_name: Optional[str] = None,
        force_refresh: bool = True,
        wait_refresh: bool = False,
    ) -> None:
        """Run dashboard refresh in a QgsTask.

        All action related to QWidget insertion or delete are not done in task.
        This is done in the _on_data_refreshed function which will be called from main thread.

        Dashboard is disabled during refresh.

        :param datastore_id: datastore id to use, defaults to None (use current datastore id)
        :type datastore_id: Optional[str], optional
        :param dataset_name: dataset name to use, defaults to None (use current dataset name)
        :type dataset_name: Optional[str], optional
        :param force_refresh: force refresh of datastore and dataset models, defaults to True
        :type force_refresh: bool, optional
        :param wait_refresh: wait for refresh before return, defaults to False
        :type wait_refresh: bool, optional
        """
        # Disable widget and define refresh in progress flag
        self.setEnabled(False)
        self.refresh_in_progress = True

        # Create task for refresh
        self.refresh_task = QgsTask.fromFunction(
            "Update data",
            self._refresh_task,
            datastore_id=datastore_id,
            dataset_name=dataset_name,
            force_refresh=force_refresh,
            on_finished=self._on_data_refreshed,
            flags=QgsTask.Flag.Hidden | QgsTask.Flag.Silent,
        )

        # Launch task
        QgsApplication.taskManager().addTask(self.refresh_task)

        # Wait for refresh if asked
        while wait_refresh and self.refresh_in_progress:
            sleep(0.1)
            QgsApplication.processEvents()

    def _on_data_refreshed(self, exception, value=None) -> None:
        """
        - Display any raised exception.
        - Update widget for displayed datastore and dataset.
        - Enable widget and update flag for refresh progress.

        :param exception: _description_
        :type exception: _type_
        :param value: _description_, defaults to None
        :type value: _type_, optional
        """
        if exception:
            QMessageBox.warning(
                self,
                self.tr("Erreur mise à jour des données."),
                self.tr(f"Erreur lors de la mise à jour des données. : {exception}"),
            )

        # Update permission content
        self.wdg_permission.refresh(
            datastore_id=self.cbx_datastore.current_datastore_id()
        )

        # Update dataset widget
        self._update_dataset_widget()

        # Enable widget
        self.setEnabled(True)
        self.refresh_in_progress = False

    def _service_selection_changed(self, selection: QItemSelection) -> None:
        """Display service details when selection changed

        :param selection: selected item
        :type selection: QItemSelection
        """
        if len(selection.indexes()) > 0:
            index = selection.indexes()[0]
            self._service_clicked(index)

    def _service_clicked(self, index: QModelIndex) -> None:
        """Display service details when clicked

        :param index: clicked index
        :type index: QModelIndex
        """
        # Hide detail zone
        self.remove_service_detail_zone()
        offering = self.mdl_offering.data(
            self.mdl_offering.index(index.row(), 0),
            Qt.ItemDataRole.UserRole,
        )
        if offering:
            self.service_detail_dialog = ServiceDetailsWidget(self)
            self.service_detail_dialog.set_offering(
                offering, self.cbx_dataset.current_dataset_name()
            )
            self.service_detail_dialog.select_stored_data.connect(
                self.select_stored_data
            )
            self.service_detail_widget_layout.addWidget(self.service_detail_dialog)

            self.service_detail_dialog.offering_deleted.connect(self._offering_deleted)
            self.service_detail_zone.show()

    def select_upload(self, upload_id: str, refresh: bool = True) -> None:
        """Select upload in table view

        :param upload_id: upload id
        :type upload_id: str
        :param refresh: force refresh before selection, defaults to True
        :type refresh: bool, optional
        """
        if refresh:
            self.refresh(wait_refresh=True, force_refresh=False)

        self.tabWidget.setCurrentWidget(self.tab_dataset)

        row = self.mdl_upload.get_upload_row(upload_id=upload_id)
        if row != -1:
            self.mdl_upload.index(row, self.mdl_upload.NAME_COL)

            # Get proxy model index for selection
            index = self.mdl_upload.index(row, self.mdl_upload.NAME_COL)

            # Update selection model
            self.tbv_upload.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            self._item_clicked(index, self.tbv_upload.model(), self.tbv_upload)

    def select_stored_data(self, stored_data_id: str, refresh: bool = True) -> None:
        """Select stored data in table view

        :param stored_data_id: stored data id
        :type stored_data_id: str
        :param refresh: force refresh before selection, defaults to True
        :type refresh: bool, optional
        """
        if refresh:
            self.refresh(wait_refresh=True, force_refresh=False)
        row = self.mdl_stored_data.get_stored_data_row(stored_data_id=stored_data_id)

        self.tabWidget.setCurrentWidget(self.tab_dataset)

        if row != -1:
            # Check all stored data table view
            for tbv in [
                self.tbv_vector_db,
                self.tbv_pyramid_vector,
                self.tbv_pyramid_raster,
            ]:
                # Get proxy model index for selection
                index = tbv.model().mapFromSource(
                    self.mdl_stored_data.index(row, self.mdl_stored_data.NAME_COL)
                )
                if index.isValid():
                    tbv.selectionModel().select(
                        index,
                        QItemSelectionModel.SelectionFlag.Select
                        | QItemSelectionModel.SelectionFlag.Rows,
                    )
                    self._item_clicked(index, tbv.model(), tbv)
                    break

    def select_offering(self, offerring_id: str, refresh: bool = True) -> None:
        """Select offering in table view

        :param offerring_id: offering id
        :type offerring_id: str
        :param refresh: force refresh before selection, defaults to True
        :type refresh: bool, optional
        """
        if refresh:
            self.refresh(wait_refresh=True, force_refresh=False)

        self.tabWidget.setCurrentWidget(self.tab_service)

        row = self.mdl_offering.get_offering_row(offering_id=offerring_id)

        if row != -1:
            self.mdl_offering.index(row, self.mdl_offering.NAME_COL)

            # Get proxy model index for selection
            index = self.mdl_offering.index(row, self.mdl_offering.NAME_COL)

            # Update selection model
            self.tbv_service.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            self._service_clicked(index)

    def _item_selection_changed(
        self, selection: QItemSelection, model: QAbstractItemModel, tbv: QTableView
    ) -> None:
        """Launch action for selected table item depending on selected item

        :param selection: selected item
        :type selection: QItemSelection
        :param model: item model
        :type model: QAbstractItemModel
        :param tbv: tableview
        :type tbv: QTableView
        """
        if len(selection.indexes()) > 0:
            index = selection.indexes()[0]
            self._item_clicked(index, model, tbv)

    def _item_clicked(
        self, index: QModelIndex, model: QAbstractItemModel, tbv: QTableView
    ) -> None:
        """
        Launch action for selected table item depending on clicked column

        Args:
            index: selected index
            proxy_model: used StoredDataProxyModel
        """
        # Remove other selections
        for table in self.tbv_list:
            if table != tbv:
                table.clearSelection()
        # Hide detail zone
        self.remove_detail_zone()
        # Get StoredData
        item = model.data(
            model.index(index.row(), 0),
            Qt.ItemDataRole.UserRole,
        )
        if item:
            if isinstance(model, StoredDataProxyModel):
                self.detail_dialog = StoredDataDetailsDialog(self)
                self.detail_dialog.set_stored_data(item)
                self.detail_widget_layout.addWidget(self.detail_dialog)
                self.detail_dialog.select_stored_data.connect(self.select_stored_data)
                self.detail_dialog.select_offering.connect(self.select_offering)
                self.detail_dialog.stored_data_deleted.connect(
                    self._stored_data_deleted
                )
                self.detail_zone.show()
            elif isinstance(model, UploadListModel):
                self.detail_dialog = UploadDetailsWidget(self)
                self.detail_dialog.set_upload(item)
                self.detail_widget_layout.addWidget(self.detail_dialog)
                self.detail_dialog.select_stored_data.connect(self.select_stored_data)
                self.detail_dialog.upload_deleted.connect(self._upload_deleted)
                self.detail_zone.show()

    def _stored_data_deleted(self, stored_data_id: str) -> None:
        """Refresh dataset after stored data delete

        :param stored_data_id: deleted stored data id
        :type stored_data_id: str
        """
        self._on_dataset_updated()

    def _upload_deleted(self, upload_id: str) -> None:
        """Refresh dataset after upload delete

        :param upload_id: deleted upload id
        :type upload_id: str
        """
        self._on_dataset_updated()

    def _offering_deleted(self, offering_id: str) -> None:
        """Refresh dataset after offering delete

        :param offering_id: deleted offering id
        :type offering_id: str
        """
        self._on_dataset_updated()

    def remove_detail_zone(self) -> None:
        """Hide detail zone and remove attached widgets"""
        # Hide detail zone
        self.detail_zone.hide()
        if self.detail_dialog:
            self.detail_widget_layout.removeWidget(self.detail_dialog)
            self.detail_dialog = None

    def remove_service_detail_zone(self) -> None:
        """Hide detail zone for service and remove attached widgets"""
        self.service_detail_zone.hide()
        if self.service_detail_dialog:
            self.service_detail_widget_layout.removeWidget(self.service_detail_dialog)
            self.service_detail_dialog = None

    def _create_dataset(self) -> None:
        """
        Show upload creation wizard with current datastore

        """
        if self.import_wizard is None:
            self.import_wizard = UploadCreationWizard(
                self, self.cbx_datastore.current_datastore_id()
            )
            self.import_wizard.finished.connect(self._del_import_wizard)
        self.import_wizard.show()

    def _add_data_to_dataset(self) -> None:
        """
        Show upload creation wizard with current datastore and dataset

        """
        if self.import_wizard is None:
            self.import_wizard = UploadCreationWizard(
                self,
                self.cbx_datastore.current_datastore_id(),
                self.cbx_dataset.current_dataset_name(),
            )
            self.import_wizard.finished.connect(self._del_import_wizard)
        self.import_wizard.show()

    def _del_import_wizard(self) -> None:
        """
        Delete import wizard

        """
        if self.import_wizard is not None:
            created_upload_id = self.import_wizard.get_created_upload_id()
            created_stored_data_id = self.import_wizard.get_created_stored_data_id()
            if created_upload_id or created_stored_data_id:
                self.refresh(
                    datastore_id=self.import_wizard.get_datastore_id(),
                    dataset_name=self.import_wizard.get_dataset_name(),
                    wait_refresh=True,
                    force_refresh=True,
                )
                # Force update of dataset. It can be unavailable because of proxy during refresh
                self.cbx_dataset.set_dataset_name(self.import_wizard.get_dataset_name())
                self._update_dataset_table()

                if created_stored_data_id:
                    self.select_stored_data(created_stored_data_id, False)
                elif created_upload_id:
                    self.select_upload(created_upload_id, False)
            self.import_wizard.deleteLater()
            self.import_wizard = None

    def _create_proxy_model(
        self,
        filter_type: List[StoredDataType],
        visible_steps: List[StoredDataStep],
        visible_status: List[StoredDataStatus],
    ) -> StoredDataProxyModel:
        """
        Create StoredDataProxyModel with filters

        Args:
            filter_type: List[StoredDataType] visible types
            visible_steps: List[StoredDataStep] visible stored data steps
            visible_status: List[StoredDataStatus] visible stored data status

        Returns: StoredDataProxyModel

        """
        proxy_mdl = StoredDataProxyModel(self)
        proxy_mdl.setSourceModel(self.mdl_stored_data)

        proxy_mdl.set_filter_type(filter_type)
        proxy_mdl.set_visible_steps(visible_steps)
        proxy_mdl.set_visible_status(visible_status)

        return proxy_mdl

    def _on_datastore_updated(self, index: int = 0) -> None:
        """
        Update stored data combobox when datastore is updated

        """
        self.refresh(
            datastore_id=self.cbx_datastore.current_datastore_id(), force_refresh=False
        )

    def _on_dataset_updated(self) -> None:
        self.refresh(
            datastore_id=self.cbx_datastore.current_datastore_id(),
            dataset_name=self.cbx_dataset.current_dataset_name(),
            force_refresh=False,
        )

    def _update_dataset_widget(self) -> None:
        # remove detail zone
        self.remove_detail_zone()
        self.remove_service_detail_zone()

        self._set_metadata_view()

    def _update_dataset_table(self) -> None:
        """
        Update stored data combobox when dataset is updated

        """
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))

        self.mdl_upload.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.mdl_stored_data.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.mdl_offering.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.mdl_document.set_datastore(
            self.cbx_datastore.current_datastore_id(),
            self.cbx_dataset.current_dataset_name(),
        )

        self.tbv_upload.resizeRowsToContents()
        # self.tbv_upload.resizeColumnsToContents()

        self.tbv_vector_db.resizeRowsToContents()
        # self.tbv_vector_db.resizeColumnsToContents()

        self.tbv_pyramid_vector.resizeRowsToContents()
        # self.tbv_pyramid_vector.resizeColumnsToContents()

        self.tbv_pyramid_raster.resizeRowsToContents()
        # self.tbv_pyramid_raster.resizeColumnsToContents()

        # For now only do a simple resize of columns
        self.tbv_service.resizeColumnsToContents()

        self.tbv_document.resizeColumnsToContents()

        QGuiApplication.restoreOverrideCursor()
