import pytest_httpserver

from geoplateforme.processing.annexes.create_annexe import CreateAnnexeAlgorithm
from tests.qgis.processings.conftest import run_alg


def test_annexe_creation(
    tmp_path,
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    annexe_file = tmp_path / "annexe.json"
    annexe_file.write_text("CONTENT")

    created_annexe_id = "created_annexe_id"
    public_paths = ["/gpf/path1", "/gpf/path2"]
    labels = ["test", "gpf"]
    datastore_id = "datastore_id"

    # Respond valid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/annexes", method="POST"
    ).respond_with_json(
        {
            "paths": public_paths,
            "size": 15000,
            "mime_type": "application/json",
            "published": True,
            "labels": labels,
            "_id": created_annexe_id,
        }
    )

    params = {
        CreateAnnexeAlgorithm.DATASTORE_ID: datastore_id,
        CreateAnnexeAlgorithm.FILE_PATH: str(annexe_file),
        CreateAnnexeAlgorithm.PUBLIC_PATHS: public_paths,
        CreateAnnexeAlgorithm.PUBLISHED: True,
        CreateAnnexeAlgorithm.LABELS: labels,
    }
    result, success = run_alg(CreateAnnexeAlgorithm().name(), params)
    assert success
    assert result[CreateAnnexeAlgorithm.CREATED_ANNEXE_ID] == created_annexe_id
