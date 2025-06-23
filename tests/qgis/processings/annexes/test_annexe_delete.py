import pytest_httpserver

from geoplateforme.processing.annexes.delete_annexe import DeleteAnnexeAlgorithm
from tests.qgis.processings.conftest import run_alg


def test_annexe_delete(
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """
    annexe_id = "annexe_id"
    datastore_id = "datastore_id"

    # Respond valid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/annexes/{annexe_id}", method="DELETE"
    ).respond_with_data(status=202)

    params = {
        DeleteAnnexeAlgorithm.DATASTORE_ID: datastore_id,
        DeleteAnnexeAlgorithm.ANNEXE_ID: annexe_id,
    }
    _, success = run_alg(DeleteAnnexeAlgorithm().name(), params)
    assert success
