# standard
import os
from functools import partial

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsProcessingAlgorithm,
    QgsProcessingAlgRunnerTask,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRectangle,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QByteArray, QSize, QTimer
from qgis.PyQt.QtGui import QIcon, QMovie, QPixmap
from qgis.PyQt.QtWidgets import QHeaderView, QMessageBox, QWizardPage

# plugin
from geoplateforme.__about__ import DIR_PLUGIN_ROOT
from geoplateforme.api.configuration import ConfigurationRequestManager
from geoplateforme.api.custom_exceptions import (
    ReadConfigurationException,
    ReadOfferingException,
    ReadStoredDataException,
    UnavailableProcessingException,
    UnavailableUploadException,
)
from geoplateforme.api.datastore import DatastoreRequestManager
from geoplateforme.api.offerings import OfferingsRequestManager
from geoplateforme.api.processing import ProcessingRequestManager
from geoplateforme.api.stored_data import StoredDataRequestManager, StoredDataStatus
from geoplateforme.gui.create_raster_tiles_from_wms_vector.qwp_tile_generation_edition import (
    TileGenerationEditionPageWizard,
)
from geoplateforme.gui.mdl_execution_list import ExecutionListModel
from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.processing.generation.create_raster_tiles_from_wms_vector import (
    RasterTilesFromWmsVectorAlgorithm,
)
from geoplateforme.processing.utils import tags_to_qgs_parameter_matrix_string
from geoplateforme.toolbelt import PlgOptionsManager


class TileGenerationStatusPageWizard(QWizardPage):
    def __init__(
        self,
        qwp_tile_generation_edition: TileGenerationEditionPageWizard,
        parent=None,
    ):
        """
        QWizardPage to create raster tile from service

        Args:
            parent: parent QObject
        """

        super().__init__(parent)
        self.setTitle(self.tr("Génération des tuiles raster en cours."))
        self.qwp_tile_generation_edition = qwp_tile_generation_edition

        uic.loadUi(
            os.path.join(os.path.dirname(__file__), "qwp_tile_generation_status.ui"),
            self,
        )
        self.tbw_errors.setVisible(False)

        # Task and feedback for tile creation
        self.create_tile_feedback = QgsProcessingFeedback()

        # Processing results
        self.created_stored_data_id = ""
        self.processing_failed = False

        # Timer for processing execution check after tile creation
        self.loading_movie = QMovie(
            str(DIR_PLUGIN_ROOT / "resources" / "images" / "loading.gif"),
            QByteArray(),
            self,
        )
        self.create_tile_check_timer = QTimer(self)
        self.create_tile_check_timer.timeout.connect(self._check_create_tile_status)

        # Model for executions display
        self.mdl_execution_list = ExecutionListModel(self)
        self.tableview_execution_list.setModel(self.mdl_execution_list)

        self.tableview_execution_list.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

    def initializePage(self) -> None:
        """
        Initialize page before show.

        """
        self.created_stored_data_id = ""
        self.processing_failed = False
        self.mdl_execution_list.clear_executions()
        self.create_tile()

    def validatePage(self) -> bool:
        """
        Validate current page and stop timer used to check status

        Returns: True

        """

        result = True

        if not self.created_stored_data_id and not self.processing_failed:
            result = False
            QMessageBox.warning(
                self,
                self.tr("La génération des tuiles raster n'a pas été lancée."),
                self.tr(
                    "La génération des tuiles raster n'a pas été lancée. Vous devez attendre le lancement avant de fermer cette fenêtre."
                ),
            )

        if result:
            self.create_tile_check_timer.stop()

        return result

    def create_tile(self) -> None:
        """
        Run RasterTilesFromWmsVectorAlgorithm with parameters defined from previous QWizardPage

        """
        algo_str = f"{GeoplateformeProvider().id()}:{RasterTilesFromWmsVectorAlgorithm().name()}"
        alg = QgsApplication.processingRegistry().algorithmById(algo_str)

        # Get offering from id
        datastore_id = self.qwp_tile_generation_edition.datastore_id
        offering_id = self.qwp_tile_generation_edition.offering_id
        manager = OfferingsRequestManager()
        try:
            offering = manager.get_offering(
                datastore=datastore_id, offering=offering_id
            )
        except ReadOfferingException as exc:
            self._report_processing_error(
                processing=self.tr("Récupération offre"), error=str(exc)
            )
            return

        # Récupération du endpoint pour avoir l'url pour le moissonnage
        datastore_manager = DatastoreRequestManager()
        try:
            datastore = datastore_manager.get_datastore(datastore_id)
            endpoint = datastore.get_endpoint_dict(endpoint_id=offering.endpoint["_id"])
        except ReadOfferingException as exc:
            self._report_processing_error(
                processing=self.tr("Récupération endpoint"), error=str(exc)
            )
            return

        if not endpoint:
            self._report_processing_error(
                processing=self.tr("Récupération endpoint"),
                error=self.tr("Endpoint {} non trouvé dans l'entrepôt").format(
                    offering.endpoint["_id"]
                ),
            )
            return

        harvest_url = None
        for url in endpoint["urls"]:
            if url["type"] == "WMS":
                harvest_url = url["url"]

        if not harvest_url:
            self._report_processing_error(
                processing=self.tr("Récupération url moissonage"),
                error=self.tr(
                    "Aucune url de type WMS trouvée pour le endpoint {}"
                ).format(offering.endpoint["_id"]),
            )
            return

        layer_name = offering.layer_name
        dataset_name = self.qwp_tile_generation_edition.dataset_name

        # Récupération de la configuration pour avoir la zone pour le moissonnage
        config_manager = ConfigurationRequestManager()
        try:
            configuration = config_manager.get_configuration(
                datastore=datastore_id, configuration=offering.configuration._id
            )
        except ReadConfigurationException as exc:
            self._report_processing_error(
                processing=self.tr("Récupération configuration"), error=str(exc)
            )
            return

        bbox = configuration.type_infos["bbox"]

        harvest_area: QgsRectangle = QgsRectangle(
            bbox["west"], bbox["south"], bbox["east"], bbox["north"]
        )

        bottom_level: int = self.qwp_tile_generation_edition.get_bottom_level()
        top_level: int = self.qwp_tile_generation_edition.get_top_level()

        harvest_levels_str = ",".join(
            [str(val) for val in reversed(range(top_level, bottom_level))]
        )

        spp = self.qwp_tile_generation_edition.get_sample_per_pixel()
        nodata = self.qwp_tile_generation_edition.get_no_data_value()

        params = {
            RasterTilesFromWmsVectorAlgorithm.DATASTORE: datastore_id,
            RasterTilesFromWmsVectorAlgorithm.HARVEST_LAYERS: layer_name,
            RasterTilesFromWmsVectorAlgorithm.HARVEST_URL: harvest_url,
            RasterTilesFromWmsVectorAlgorithm.STORED_DATA_NAME: self.qwp_tile_generation_edition.lne_name.text(),
            RasterTilesFromWmsVectorAlgorithm.BOTTOM: bottom_level,
            RasterTilesFromWmsVectorAlgorithm.TOP: top_level,
            RasterTilesFromWmsVectorAlgorithm.HARVEST_LEVELS: harvest_levels_str,
            RasterTilesFromWmsVectorAlgorithm.HARVEST_AREA: harvest_area,
            RasterTilesFromWmsVectorAlgorithm.SAMPLES_PER_PIXEL: spp,
            RasterTilesFromWmsVectorAlgorithm.NODATA: nodata,
            RasterTilesFromWmsVectorAlgorithm.WAIT_FOR_GENERATION: False,
            RasterTilesFromWmsVectorAlgorithm.TAGS: tags_to_qgs_parameter_matrix_string(
                {"datasheet_name": dataset_name}
            ),
        }

        if self.qwp_tile_generation_edition.use_api_key:
            params[RasterTilesFromWmsVectorAlgorithm.HARVEST_EXTRA] = (
                f"apikey={self.qwp_tile_generation_edition.get_api_key()}"
            )

        self.lbl_step_icon.setMovie(self.loading_movie)
        self.loading_movie.start()

        self._run_alg(
            alg, params, self.create_tile_feedback, self._create_tile_finished
        )

        # Run timer for tile creation check
        self.create_tile_check_timer.start(
            int(PlgOptionsManager.get_plg_settings().status_check_sleep * 1000.0)
        )

    def _create_tile_finished(self, context, successful, results):
        """
        Callback executed when TileCreationAlgorithm is finished

        Args:
            context:  algorithm context
            successful: algorithm success
            results: algorithm results
        """
        if successful:
            self.created_stored_data_id = results[
                RasterTilesFromWmsVectorAlgorithm.CREATED_STORED_DATA_ID
            ]

            self.setTitle(
                self.tr(
                    "Génération des tuiles raster en cours.\nVous pouvez fermer la fenêtre pendant la génération."
                )
            )
            # Emit completeChanged to update finish button
            self.completeChanged.emit()
        else:
            self._report_processing_error(
                self.tr("Génération des tuiles raster"),
                self.create_tile_feedback.textLog(),
            )

    def _check_create_tile_status(self):
        """
        Check tile creation status

        """
        self.mdl_execution_list.clear_executions()

        if self.created_stored_data_id:
            try:
                processing_manager = ProcessingRequestManager()
                stored_data_manager = StoredDataRequestManager()
                datastore_id = self.qwp_tile_generation_edition.datastore_id

                stored_data = stored_data_manager.get_stored_data(
                    datastore_id=datastore_id,
                    stored_data_id=self.created_stored_data_id,
                )

                # Stop timer if stored_data generated
                status = stored_data.status
                if status == StoredDataStatus.GENERATED:
                    self.create_tile_check_timer.stop()
                    self.loading_movie.stop()
                    self.setTitle(self.tr("Your tiles are ready."))
                    pixmap = QPixmap(
                        str(
                            DIR_PLUGIN_ROOT
                            / "resources"
                            / "images"
                            / "icons"
                            / "Done.svg"
                        )
                    )
                    self.lbl_step_icon.setMovie(QMovie())
                    self.lbl_step_icon.setPixmap(pixmap)
                elif status == StoredDataStatus.UNSTABLE:
                    self._stop_timer_and_display_error(
                        self.tr(
                            "Stored data creation failed. Check report in "
                            "dashboard for more details."
                        )
                    )
                if (
                    stored_data.tags is not None
                    and "proc_pyr_creat_id" in stored_data.tags.keys()
                ):
                    execution = processing_manager.get_execution(
                        datastore_id=datastore_id,
                        exec_id=stored_data.tags["proc_pyr_creat_id"],
                    )

                    self.mdl_execution_list.set_execution_list([execution])
            except (
                ReadStoredDataException,
                UnavailableProcessingException,
                UnavailableUploadException,
            ) as exc:
                self._report_processing_error(
                    self.tr("Stored data check status"), str(exc)
                )

    def _stop_timer_and_display_error(self, error: str) -> None:
        self.create_tile_check_timer.stop()
        self.setTitle(error)
        self.loading_movie.stop()
        self.lbl_step_icon.setMovie(QMovie())
        self.lbl_step_icon.setPixmap(
            QIcon(QgsApplication.iconPath("mIconWarning.svg")).pixmap(QSize(32, 32))
        )
        self.completeChanged.emit()

    def _report_processing_error(self, processing: str, error: str) -> None:
        """
        Report processing error by displaying error in text browser

        Args:
            error:
        """
        self.processing_failed = True
        self.tbw_errors.setVisible(True)
        self.tbw_errors.setText(error)
        self._stop_timer_and_display_error(
            self.tr("{0} failed. Check report for more details.").format(processing)
        )

    @staticmethod
    def _run_alg(
        alg: QgsProcessingAlgorithm,
        params: {},
        feedback: QgsProcessingFeedback,
        executed_callback,
    ) -> int:
        """
        Run a QgsProcessingAlgorithm and connect execution callback

        Args:
            alg: QgsProcessingAlgorithm to run
            params: QgsProcessingAlgorithm params
            feedback: QgsProcessingFeedback
            executed_callback: executed callback after algorithm execution

        Returns: created QgsTask id

        """
        context = QgsProcessingContext()
        task = QgsProcessingAlgRunnerTask(alg, params, context, feedback)
        task.executed.connect(partial(executed_callback, context))
        return QgsApplication.taskManager().addTask(task)
