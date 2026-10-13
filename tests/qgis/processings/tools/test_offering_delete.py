import pytest_httpserver

from geoplateforme.processing.tools.delete_offering import DeleteOfferingAlgorithm
from tests.qgis.processings.conftest import run_alg

OFFERING_ID = "offering_id"
CONFIGURATION_ID = "configuration_id"

OFFERING_JSON = {
    "open": True,
    "available": True,
    "layer_name": "SANDBOX_pyr_raster_wms_raster_3",
    "type": "WMS-RASTER",
    "status": "PUBLISHED",
    "configuration": {
        "name": "pyr_raster_wms_raster_3",
        "status": "PUBLISHED",
        "_id": CONFIGURATION_ID,
    },
    "endpoint": {
        "name": "Service de diffusion WMS Raster Bac à Sable",
        "_id": "52964d9c-dc3c-48e3-a87e-754937583216",
    },
    "urls": [
        {
            "type": "WMS",
            "url": "https://data.geopf.fr/sandbox/wms-r?service=WMS&version=1.3.0&request=GetMap&layers=SANDBOX_pyr_raster_wms_raster_3&bbox={xmin},{ymin},{xmax},{ymax}&styles={styles}&width={width}&height={height}&srs={srs}&format={format}",
        }
    ],
    "_id": OFFERING_ID,
}

CONFIGURATION_JSON = {
    "creation": "2025-08-12T13:17:33.659260Z",
    "update": "2025-08-12T13:17:45.255108Z",
    "name": "SANDBOX_pyr_raster_wms_raster_3",
    "layer_name": "SANDBOX_pyr_raster_wms_raster_3",
    "type": "WMS-RASTER",
    "status": "PUBLISHED",
    "tags": {},
    "attribution": {},
    "last_event": {
        "title": "Publication",
        "text": "Publication de la couche 'SANDBOX_wms_vector' sur le point d'accès WMS_VECTOR 'Service de diffusion WMS Vecteur Bac à Sable'",
        "date": "2025-08-12T13:17:38.548758",
        "initiator": {
            "last_name": "KERLOCH",
            "first_name": "Jean-Marie",
            "_id": "e29d7c1d-d315-4576-b9c0-964cb347d625",
        },
        "urls": [
            {
                "type": "WMS",
                "url": "https://data.geopf.fr/sandbox/wms-v?service=WMS&version=1.3.0&request=GetMap&layers=SANDBOX_wms_vector&bbox={xmin},{ymin},{xmax},{ymax}&styles={styles}&width={width}&height={height}&srs={srs}&format={format}",
            }
        ],
    },
    "_id": CONFIGURATION_ID,
    "metadata": [],
    "type_infos": {},
}


def test_no_error(
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    datastore_id = "valid_datastore"
    offering_id = OFFERING_ID
    configuration_id = CONFIGURATION_ID

    # Get offering for configuration id definition
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="GET"
    ).respond_with_json(OFFERING_JSON, status=200)

    # Get configuration for dataset definition. No dataset to avoid mock of metadata unpublish
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/configurations/{configuration_id}",
        method="GET",
    ).respond_with_json(CONFIGURATION_JSON, status=200)

    # Delete offering
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="DELETE"
    ).respond_with_data(status=202)

    # Return invalid status code to indicate that offering is deleted
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="GET"
    ).respond_with_data(status=500)

    # List of offering for configuration
    headers = {
        "Content-Range": "0-0/0",
    }
    data_geopf_srv.expect_oneshot_request(
        uri=f"/api/datastores/{datastore_id}/offerings",
        query_string=f"limit=1&configuration={configuration_id}",
        method="GET",
    ).respond_with_json(
        {},
        status=202,
        headers=headers,
    )
    # Delete configuration
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/configurations/{configuration_id}",
        method="DELETE",
    ).respond_with_data(status=202)

    params = {
        DeleteOfferingAlgorithm.DATASTORE: datastore_id,
        DeleteOfferingAlgorithm.OFFERING: offering_id,
    }
    _, success = run_alg(DeleteOfferingAlgorithm().name(), params)
    assert success


def test_unpublished_offering_delete(
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """Check deletion succeeds when the offering is already UNPUBLISHED."""

    datastore_id = "valid_datastore"
    offering_id = OFFERING_ID
    configuration_id = CONFIGURATION_ID

    unpublished_offering = dict(OFFERING_JSON)
    unpublished_offering["status"] = "UNPUBLISHED"

    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="GET"
    ).respond_with_json(unpublished_offering, status=200)

    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/offerings/{offering_id}", method="DELETE"
    ).respond_with_data(status=202)

    headers = {
        "Content-Range": "0-0/0",
    }
    data_geopf_srv.expect_oneshot_request(
        uri=f"/api/datastores/{datastore_id}/offerings",
        query_string=f"limit=1&configuration={configuration_id}",
        method="GET",
    ).respond_with_json({}, status=202, headers=headers)

    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/configurations/{configuration_id}",
        method="DELETE",
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
