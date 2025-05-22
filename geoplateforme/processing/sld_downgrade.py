# standard

from pathlib import Path

from lxml import etree
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
)
from qgis.PyQt.QtCore import QCoreApplication

# Plugin
from geoplateforme.processing.utils import get_short_string, get_user_manual_url

# PyQGIS


class SldDowngradeAlgorithm(QgsProcessingAlgorithm):
    FILE_PATH = "FILE_PATH"
    CHECK_INPUT = "CHECK_INPUT"
    CHECK_OUTPUT = "CHECK_OUTPUT"
    OUTPUT = "OUTPUT"

    def tr(self, message: str) -> str:
        """Get the translation for a string using Qt translation API.

        :param message: string to be translated.
        :type message: str

        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate(self.__class__.__name__, message)

    def createInstance(self):
        return SldDowngradeAlgorithm()

    def name(self):
        return "sld_downgrade"

    def displayName(self):
        return self.tr(
            "Mise à jour fichier .sld pour passer d'une version 1.1.0 à 1.0.0"
        )

    def group(self):
        return self.tr("")

    def groupId(self):
        return ""

    def helpUrl(self):
        return get_user_manual_url(self.name())

    def shortHelpString(self):
        return get_short_string(self.name(), self.displayName())

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.FILE_PATH,
                self.tr("Fichier style Geoserver"),
                fileFilter="Fichier style Geoserver (*.sld)",
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CHECK_INPUT,
                self.tr("Vérification du format .sld 1.1.0 en entrée"),
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CHECK_OUTPUT,
                self.tr("Vérification du format .sld 1.0.0 en sortie"),
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                name=self.OUTPUT,
                description=self.tr("Fichier converti"),
                fileFilter="*.sld",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        file_path = self.parameterAsFile(parameters, self.FILE_PATH, context)
        output_file_path = self.parameterAsFile(parameters, self.OUTPUT, context)
        check_input = self.parameterAsBool(parameters, self.CHECK_INPUT, context)
        check_output = self.parameterAsBool(parameters, self.CHECK_OUTPUT, context)

        # This xls transform file comes from https://stackoverflow.com/questions/45860004/converting-sld-from-1-1-to-1-0-via-python
        # Supported transformation
        # - Change the version and the schemaLocation values
        # - Map SvgParameter elements in the http://www.opengis.net/se namespace to CssParameter in the http://www.opengis.net/sld namespace
        # - Map remaining http://www.opengis.net/se elements and attributes to the http://www.opengis.net/sld namespace
        transform_file = Path(__file__).parent / "sld11-10.xsl"
        transform = etree.XSLT(etree.parse(transform_file))

        sour_doc = etree.parse(file_path)
        if check_input:
            feedback.pushInfo(self.tr("Vérification format sld 1.1.0 en entrée"))
            sld11 = etree.XMLSchema(
                etree.parse(
                    "http://schemas.opengis.net/sld/1.1.0/StyledLayerDescriptor.xsd"
                )
            )
            if not sld11.validate(sour_doc):
                raise QgsProcessingException(
                    self.tr(
                        "Fichier {} n'est pas conforme à la norme SLD 1.1.0 : {}".format(
                            file_path, sld11.error_log.last_error
                        )
                    )
                )

        feedback.pushInfo(self.tr("Application transformation"))
        dest_doc = transform(sour_doc)
        if check_output:
            sld10 = etree.XMLSchema(
                etree.parse(
                    "http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd"
                )
            )
            if not sld10.validate(dest_doc):
                raise QgsProcessingException(
                    self.tr(
                        "Le résultat de la transformation n'est pas conforme à la norme SLD 1.1.0 : {}".format(
                            file_path,
                        )
                    )
                )

        feedback.pushInfo(self.tr("Ecriture fichier résultat"))
        dest_doc.write(
            output_file_path, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )

        return {}
