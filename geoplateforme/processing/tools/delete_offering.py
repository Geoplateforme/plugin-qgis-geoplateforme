# standard

# PyQGIS

from time import sleep
from typing import Optional

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.api.configuration import ConfigurationRequestManager
from geoplateforme.api.custom_exceptions import (
    MetadataUnpublishException,
    ReadConfigurationException,
    ReadMetadataException,
    ReadOfferingException,
    UnavailableConfigurationException,
    UnavailableOfferingsException,
)
from geoplateforme.api.datastore import DatastoreRequestManager
from geoplateforme.api.metadata import MetadataRequestManager
from geoplateforme.api.offerings import OfferingsRequestManager, OfferingStatus
from geoplateforme.processing.utils import get_short_string, get_user_manual_url


class DeleteOfferingAlgorithm(QgsProcessingAlgorithm):
    DATASTORE = "DATASTORE"
    OFFERING = "OFFERING"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return DeleteOfferingAlgorithm()

    def name(self):
        return "delete_offering"

    def displayName(self):
        return self.tr("Suppression d'une offre")

    def group(self):
        return self.tr("Outils géoplateforme")

    def groupId(self):
        return "tools"

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                name=self.DATASTORE,
                description=self.tr("Identifiant de l'entrepôt"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.OFFERING,
                description=self.tr("Identifiant de l'offre"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        datastore_id = self.parameterAsString(parameters, self.DATASTORE, context)
        offering_id = self.parameterAsString(parameters, self.OFFERING, context)

        manager_offer = OfferingsRequestManager()
        try:
            feedback.pushInfo(self.tr("Récupération de l'offre"))
            offering = manager_offer.get_offering(datastore_id, offering_id)

        except ReadOfferingException as exc:
            raise QgsProcessingException(
                self.tr("Erreur lors de la récupération de l'offre : {}").format(exc)
            ) from exc

        dataset_name: Optional[str] = offering.configuration.tags.get(
            "datasheet_name", None
        )

        try:
            feedback.pushInfo(self.tr("Suppression de l'offre"))
            manager_offer = OfferingsRequestManager()
            manager_offer.delete_offering(datastore_id, offering_id)

        except UnavailableOfferingsException as exc:
            raise QgsProcessingException(
                self.tr("Erreur lors de la suppression de l'offre : {}").format(exc)
            ) from exc

        feedback.pushInfo(self.tr("Attente dépublication de l'offre"))
        unpublishing = True
        while unpublishing:
            try:
                offering = manager_offer.get_offering(
                    datastore=datastore_id, offering=offering_id
                )
                if offering.status != OfferingStatus.UNPUBLISHING:
                    raise QgsProcessingException(
                        self.tr(
                            "L'offre {} n'est pas en cours de dépublication. La suppression de la configuration associée est annulée."
                        ).format(offering_id)
                    )
            except ReadOfferingException:
                unpublishing = False
            if unpublishing:
                sleep(1)

        # Check if configuration is associated to another offering
        try:
            feedback.pushInfo(
                self.tr("Récupération des offres associés à la même configuration")
            )
            offering_list = manager_offer.get_offering_list(
                datastore_id=datastore_id,
                configuration_id=offering.configuration._id,
            )

        except ReadOfferingException as exc:
            raise QgsProcessingException(
                self.tr(
                    "Erreur lors de la récupération des offres de la configuration : {}"
                ).format(exc)
            ) from exc

        if len(offering_list) == 0:
            feedback.pushInfo(
                self.tr("Suppression de la configuration associée à l'offre")
            )
            manager_config = ConfigurationRequestManager()
            try:
                manager_config.delete_configuration(
                    datastore=datastore_id,
                    configuration_id=offering.configuration._id,
                )

            except UnavailableConfigurationException as exc:
                raise QgsProcessingException(
                    self.tr(
                        "Erreur lors de la suppression de la configuration associée à l'offre : {}"
                    ).format(exc)
                ) from exc

            # Check if dataset is defined to check if other configuration are available
            if dataset_name:
                try:
                    feedback.pushInfo(
                        self.tr("Récupération des configuration associées au dataset")
                    )
                    tags = {"datasheet_name": dataset_name}
                    remaining_configurations = manager_config.get_configuration_list(
                        datastore_id=datastore_id,
                        tags=tags,
                    )
                except ReadConfigurationException as exc:
                    raise QgsProcessingException(
                        self.tr(
                            "Erreur lors de la récupération des autres configuration associées au dataset : {}"
                        ).format(exc)
                    ) from exc

                if len(remaining_configurations) == 0:
                    feedback.pushInfo(
                        self.tr(
                            "Aucune configuration disponible dans le dataset, dépublication de la métadata"
                        )
                    )
                    manager = MetadataRequestManager()
                    tags = {"datasheet_name": dataset_name}

                    try:
                        metadatas = manager._get_metadata_list(
                            datastore_id=datastore_id, tags=tags
                        )
                    except ReadMetadataException as exc:
                        raise QgsProcessingException(
                            self.tr(
                                "Erreur lors de la récupération des metadatas associées au dataset : {}"
                            ).format(exc)
                        ) from exc

                    if len(metadatas) == 1:
                        try:
                            metadata = metadatas[0]

                            # get the endpoint for the publication
                            datastore_manager = DatastoreRequestManager()
                            datastore = datastore_manager.get_datastore(datastore_id)
                            metadata_endpoint_id = datastore.get_endpoint(
                                data_type="METADATA"
                            )

                            # Unpublish metadata
                            manager.unpublish(
                                datastore_id=datastore_id,
                                endpoint_id=metadata_endpoint_id,
                                metadata_file_identifier=metadata.file_identifier,
                            )

                        except MetadataUnpublishException as exc:
                            raise QgsProcessingException(
                                self.tr(
                                    "Erreur lors de la dépublication de la metadata associée au dataset : {}"
                                ).format(exc)
                            ) from exc
                    else:
                        feedback.pushWarning(
                            self.tr("Aucune métadata disponible pour le dataset")
                        )

        return {}
