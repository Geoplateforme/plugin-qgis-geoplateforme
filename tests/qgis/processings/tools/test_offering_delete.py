import pytest_httpserver

from geoplateforme.processing.tools.delete_offering import DeleteOfferingAlgorithm
from tests.qgis.processings.conftest import run_alg


def test_no_error(
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    datastore_id = "valid_datastore"
    offering_id = "valid_offering"

    # Respond valid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="DELETE"
    ).respond_with_data(status=202)

    params = {
        DeleteOfferingAlgorithm.DATASTORE: datastore_id,
        DeleteOfferingAlgorithm.OFFERING: offering_id,
    }
    _, success = run_alg(DeleteOfferingAlgorithm().name(), params)
    assert success


def test_invalid_input_error(data_geopf_srv: pytest_httpserver.HTTPServer):
    """
    Check error is raised when server return invalid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    datastore_id = "invalid_datastore"
    offering_id = "invalid_offering"

    # Respond invalid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="DELETE"
    ).respond_with_data(status=404)

    params = {
        DeleteOfferingAlgorithm.DATASTORE: datastore_id,
        DeleteOfferingAlgorithm.OFFERING: offering_id,
    }
    _, success = run_alg(DeleteOfferingAlgorithm().name(), params)
    assert not success
