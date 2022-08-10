import json

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geotuileur.api.offerings import OfferingsRequestManager


class DepublicationAlgorithm(QgsProcessingAlgorithm):

    INPUT_JSON = "INPUT_JSON"
    DATASTORE = "datastore"
    STORED_DATA = "stored data"

    def tr(self, string):
        return QCoreApplication.translate(
            "Create an depublication for IGN Geotuileur platform", string
        )

    def createInstance(self):
        return DepublicationAlgorithm()

    def name(self):
        return "depublication"

    def displayName(self):
        return self.tr("Create depublication")

    def group(self):
        return self.tr("")

    def groupId(self):
        return ""

    def helpUrl(self):
        return ""

    def shortHelpString(self):
        return self.tr(
            "Delete publication in geotuileur platform.\n"
            "Input parameters are defined in a .json file.\n"
            "Available parameters:\n"
            "{\n"
            f'    "{self.DATASTORE}": datastore id (str),\n'
            f'    "{self.STORED_DATA}": stored data(str),\n'
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                name=self.INPUT_JSON,
                description=self.tr("Input .json file"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        filename = self.parameterAsFile(parameters, self.INPUT_JSON, context)

        # load processing depublication from the JSON

        with open(filename, "r") as file:
            data = json.load(file)
            datastore = data.get(self.DATASTORE)
            stored_data = data.get(self.STORED_DATA)

            # Getting and delete offering and configuration

        try:
            offering_id_manager = OfferingsRequestManager()
            offering_ids = offering_id_manager.get_offerings_id(datastore, stored_data)
            configuration_ids = offering_id_manager.get_configurations_id(
                datastore, stored_data
            )
            offering_id_manager.delete_publication(datastore, offering_ids)
            offering_id_manager.delete_configuration(datastore, configuration_ids)

        except OfferingsRequestManager.UnavailableOfferingsException as exc:
            raise QgsProcessingException(f"exc depublication : {exc}")

        return {}
