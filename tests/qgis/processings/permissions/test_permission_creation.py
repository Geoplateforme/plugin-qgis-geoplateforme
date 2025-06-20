import pytest_httpserver

from geoplateforme.processing.permissions.create_permission import (
    CreatePermissionAlgorithm,
)
from tests.qgis.processings.conftest import run_alg

OFFERINGS_RESPONSE = [
    {
        "type": "WMTS-TMS",
        "status": "PUBLISHED",
        "layer_name": "test_layer_name",
        "open": False,
        "available": True,
        "_id": "offerring_id",
    }
]
DATASTORE_AUTHOR_RESPONSE = {
    "name": "datastore_name",
    "technical_name": "datastore_technical_name",
    "active": True,
    "_id": "datastore_id",
}


def test_account_creation(
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    datastore_id = "valid_datastore"
    licence = "test_no_error"

    created_permission_id = "permission_id"

    # Respond valid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/permissions", method="POST"
    ).respond_with_json(
        [
            {
                "licence": licence,
                "offerings": OFFERINGS_RESPONSE,
                "datastore_author": DATASTORE_AUTHOR_RESPONSE,
                "beneficiary": {
                    "_id": "e29d7c1d-d315-4576-b9c0-964cb347d625",
                    "last_name": "KERLOCH",
                    "first_name": "Jean-Marie",
                },
                "only_oauth": False,
                "_id": created_permission_id,
            }
        ]
    )

    params = {
        CreatePermissionAlgorithm.DATASTORE: datastore_id,
        CreatePermissionAlgorithm.LICENCE: licence,
        CreatePermissionAlgorithm.PERMISSION_TYPE: "ACCOUNT",
        CreatePermissionAlgorithm.USER_OR_COMMUNITIES: "valid_user",
        CreatePermissionAlgorithm.OFFERINGS: "valid_offering",
    }
    result, success = run_alg(CreatePermissionAlgorithm().name(), params)
    assert success
    assert result[CreatePermissionAlgorithm.CREATED_PERMISSIONS_ID] == ",".join(
        [created_permission_id]
    )


def test_community_creation(
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    datastore_id = "valid_datastore"
    licence = "test_no_error"
    created_permission_id = "permission_id"

    # Respond valid return code
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/permissions", method="POST"
    ).respond_with_json(
        [
            {
                "licence": licence,
                "offerings": OFFERINGS_RESPONSE,
                "datastore_author": DATASTORE_AUTHOR_RESPONSE,
                "beneficiary": {
                    "_id": "e29d7c1d-d315-4576-b9c0-964cb347d625",
                    "technical_name": "my_community",
                    "name": "My community",
                },
                "only_oauth": False,
                "_id": created_permission_id,
            }
        ]
    )

    params = {
        CreatePermissionAlgorithm.DATASTORE: datastore_id,
        CreatePermissionAlgorithm.LICENCE: licence,
        CreatePermissionAlgorithm.PERMISSION_TYPE: "COMMUNITY",
        CreatePermissionAlgorithm.USER_OR_COMMUNITIES: "valid_community",
        CreatePermissionAlgorithm.OFFERINGS: "valid_offering",
    }
    result, success = run_alg(CreatePermissionAlgorithm().name(), params)
    assert success
    assert result[CreatePermissionAlgorithm.CREATED_PERMISSIONS_ID] == ",".join(
        [created_permission_id]
    )
