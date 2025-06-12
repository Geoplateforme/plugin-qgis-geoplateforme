from typing import Any, Dict, Tuple

import pytest
import pytest_httpserver
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback

from geoplateforme.processing import GeoplateformeProvider
from geoplateforme.toolbelt.preferences import PlgSettingsStructure

SRV_URL = "http://localhost:5000/api"


class QgsProcessingFeedBackTest(QgsProcessingFeedback):
    def __init__(self):
        """
        QgsProcessingFeedback to store calls from QgsProcessingAlgorithm

        """
        super().__init__()
        self.progressTexts = []
        self.warnings = []
        self.infos = []
        self.commandInfos = []
        self.debugInfos = []
        self.consoleInfos = []
        self.reportErrors = []

    def setProgressText(self, text: str):
        self.progressTexts.append(text)

    def pushWarning(self, warning: str):
        self.warnings.append(warning)

    def pushInfo(self, info: str):
        self.infos.append(info)

    def pushCommandInfo(self, info: str):
        self.commandInfos.append(info)

    def pushDebugInfo(self, info):
        self.debugInfos.append(info)

    def pushConsoleInfo(self, info: str):
        self.consoleInfos.append(info)

    def reportError(self, error: str, fatalError=False):
        self.reportErrors.append(error)


@pytest.fixture(autouse=True)
def add_provider(qgis_processing) -> GeoplateformeProvider:
    """
    Add GeoplateformeProvider to processing registry and remove it after use

    Args:
        qgis_processing: pytest-qgis fixture to initialize qgis processing
    """
    prov = GeoplateformeProvider()
    QgsApplication.processingRegistry().addProvider(prov)
    yield prov
    QgsApplication.processingRegistry().removeProvider(prov)


def start_srv(host: str, port: int) -> pytest_httpserver.HTTPServer:
    """Start simulating a server with pytest_httpserver
    Server is stopped after use

    :param host: server host
    :type host: str
    :param port: server port
    :type port: int
    :yield: server started
    :rtype: pytest_httpserver.HTTPServer
    """
    server = pytest_httpserver.HTTPServer(host=host, port=port, ssl_context=None)
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.fixture
def data_geopf_srv(monkeypatch) -> pytest_httpserver.HTTPServer:
    """Fixture to start simulating data.geopf.fr server and monkeypatch plugin settings for url

    :param monkeypatch: monkeypatch for PlgSettingsStructure
    :type monkeypatch: MonkeyPatch
    :yield: server started
    :rtype: pytest_httpserver.HTTPServer
    """
    server = start_srv("127.0.0.1", 5000)
    monkeypatch.setattr(PlgSettingsStructure, "base_url_api_entrepot", SRV_URL)
    yield from server


def run_alg(
    alg_name: str, params: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool | None]:
    """Run plugin algorithm and return result

    :param alg_name: algorithm name
    :type alg_name: str
    :param params: algorithm parameters
    :type params: Dict[str, Any]
    :return: algorithm result
    :rtype: Tuple[Dict[str, Any], bool | None]
    """
    algo_str = f"{GeoplateformeProvider().id()}:{alg_name}"
    alg = QgsApplication.processingRegistry().algorithmById(algo_str)
    assert alg is not None

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    return alg.run(params, context, feedback)
