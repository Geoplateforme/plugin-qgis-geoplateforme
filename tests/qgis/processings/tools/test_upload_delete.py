import pytest_httpserver

from geoplateforme.processing.tools.delete_upload import DeleteUploadAlgorithm
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
    upload_id = "valid_upload"

    # Respond valid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/uploads/{upload_id}", method="DELETE"
    ).respond_with_data(status=202)

    params = {
        DeleteUploadAlgorithm.DATASTORE: datastore_id,
        DeleteUploadAlgorithm.UPLOAD: upload_id,
    }
    _, success = run_alg(DeleteUploadAlgorithm().name(), params)
    assert success


def test_invalid_input_error(data_geopf_srv: pytest_httpserver.HTTPServer):
    """
    Check error is raised when server return invalid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    datastore_id = "invalid_datastore"
    upload_id = "invalid_upload"
    params = {
        DeleteUploadAlgorithm.DATASTORE: datastore_id,
        DeleteUploadAlgorithm.UPLOAD: upload_id,
    }

    # Respond invalid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/uploads/{upload_id}", method="DELETE"
    ).respond_with_data(status=404)

    params = {
        DeleteUploadAlgorithm.DATASTORE: datastore_id,
        DeleteUploadAlgorithm.UPLOAD: upload_id,
    }
    _, success = run_alg(DeleteUploadAlgorithm().name(), params)
    assert not success
