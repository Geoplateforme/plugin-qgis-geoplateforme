import pytest_httpserver

from geoplateforme.processing.style.add_configuration_style import (
    AddConfigurationStyleAlgorithm,
)
from tests.qgis.processings.conftest import run_alg

DATASTORE_ID = "datastore_id"
DATASTORE_JSON = {
    "community": {
        "contact": "contact@ign.fr",
        "_id": "1a81d09d-fe5d-4940-a12f-264b6f17a255",
        "public": False,
    },
    "processings": [],
    "name": "datastore_name",
    "technical_name": "datastore_tech_name",
    "endpoints": [],
    "storages": {},
    "metadata_file_identifier_prefix": "SANDBOX",
    "configuration_layer_name_prefix": "SANDBOX",
    "sharings": False,
    "_id": DATASTORE_ID,
    "checks": [],
    "active": True,
}

CONFIGURATION_ID = "configuration_id"
CONFIGURATION_JSON = {
    "name": "SANDBOX.nouveau_service_public",
    "layer_name": "SANDBOX.nouveau_service_public",
    "type": "WMTS-TMS",
    "status": "PUBLISHED",
    "tags": {"datasheet_name": "test_jmk_windows"},
    "last_event": {
        "title": "Synchronisation",
        "text": "Synchronisation des informations de configuration et de données",
        "date": "2025-06-23T12:42:50.413483",
        "initiator": {
            "last_name": "KERLOCH",
            "first_name": "Jean-Marie",
            "_id": "e29d7c1d-d315-4576-b9c0-964cb347d625",
        },
    },
    "_id": CONFIGURATION_ID,
    "extra": {
        "styles": [
            {
                "name": "test",
                "layers": [
                    {
                        "url": "https://data.geopf.fr/annexes/ign_recette/style/4870b5fd-20c9-4245-8b93-e24072cd1710.json",
                        "annexe_id": "fb27d7f8-8e89-4cb4-9684-25ec26c7f4f9",
                    }
                ],
            },
            {
                "name": "test_json_mapbox",
                "layers": [
                    {
                        "url": "https://data.geopf.fr/annexes/ign_recette/style/62fe4213-fb5c-4c79-899c-189e45f94f68.json",
                        "annexe_id": "695eccf3-2baf-4844-923e-a5b1c35c0c29",
                    }
                ],
            },
            {
                "name": "new_style_plugin",
                "layers": [
                    {
                        "url": "https://data.geopf.fr/annexes/ign_recette/style/8061a358-91b9-421c-b2d1-fc5139856406.json",
                        "annexe_id": "85a974f1-2a7f-45df-8e67-7777494d201e",
                    }
                ],
                "current": True,
            },
        ]
    },
    "metadata": [
        {
            "format": "application/json",
            "url": "https://data.geopf.fr/annexes/ign_recette/style/4870b5fd-20c9-4245-8b93-e24072cd1710.json",
            "type": "Other",
        },
        {
            "format": "application/json",
            "url": "https://data.geopf.fr/annexes/ign_recette/style/62fe4213-fb5c-4c79-899c-189e45f94f68.json",
            "type": "Other",
        },
    ],
    "type_infos": {
        "bbox": {
            "west": -3.5349993102856128,
            "south": 46.355,
            "east": 2.157499310285613,
            "north": 49.20148368028561,
        },
        "title": "SANDBOX.nouveau_service_public",
        "keywords": ["Climatologie, météorologie, atmosphère"],
        "styles": [],
        "used_data": [
            {
                "bottom_level": "18",
                "top_level": "5",
                "stored_data": "b9774947-9345-4cfa-855e-ea32ad501ce9",
            }
        ],
        "abstract": '"SANDBOX.nouveau_service_prive"',
    },
}


def test_add_configuration_style(
    tmp_path,
    data_geopf_srv: pytest_httpserver.HTTPServer,
):
    """
    Check no error is raised when server return valid return code

    Args:
        data_geopf_srv: pytest fixture to simulate server and mock plugin settings
    """

    annexe_file_1 = tmp_path / "annexe_1.json"
    annexe_file_1.write_text("CONTENT")

    annexe_file_2 = tmp_path / "annexe_2.json"
    annexe_file_2.write_text("CONTENT")

    annexes_files = [str(annexe_file_1), str(annexe_file_2)]
    annexes_files_str = ",".join(annexes_files)

    layer_style_names = ["layer1", "layer2"]
    layer_style_names_str = ",".join(layer_style_names)

    created_annexe_id_1 = "annexe_id_1"
    created_annexe_id_2 = "annexe_id_2"
    datastore_id = DATASTORE_ID
    configuration_id = CONFIGURATION_ID

    # Annexe creation
    public_paths = ["/gpf/path1", "/gpf/path2"]
    labels = ["test", "gpf"]
    data_geopf_srv.expect_ordered_request(
        f"/api/datastores/{datastore_id}/annexes", method="POST"
    ).respond_with_json(
        {
            "paths": public_paths,
            "size": 15000,
            "mime_type": "application/json",
            "published": True,
            "labels": labels,
            "_id": created_annexe_id_1,
        }
    )
    public_paths = ["/gpf/path1", "/gpf/path2"]
    labels = ["test", "gpf"]
    data_geopf_srv.expect_ordered_request(
        f"/api/datastores/{datastore_id}/annexes", method="POST"
    ).respond_with_json(
        {
            "paths": public_paths,
            "size": 15000,
            "mime_type": "application/json",
            "published": True,
            "labels": labels,
            "_id": created_annexe_id_2,
        }
    )

    # Configuration request
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/configurations/{configuration_id}",
        method="GET",
    ).respond_with_json(CONFIGURATION_JSON)

    # Datastore request
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}", method="GET"
    ).respond_with_json(DATASTORE_JSON)

    # Configuration modification
    data_geopf_srv.expect_oneshot_request(
        f"/api/datastores/{datastore_id}/configurations/{configuration_id}",
        method="PATCH",
    ).respond_with_data(status=202)

    params = {
        AddConfigurationStyleAlgorithm.DATASTORE_ID: datastore_id,
        AddConfigurationStyleAlgorithm.CONFIGURATION_ID: configuration_id,
        AddConfigurationStyleAlgorithm.STYLE_NAME: "test_name",
        AddConfigurationStyleAlgorithm.DATASET_NAME: "datasetname",
        AddConfigurationStyleAlgorithm.STYLE_FILE_PATHS: annexes_files_str,
        AddConfigurationStyleAlgorithm.LAYER_STYLE_NAMES: layer_style_names_str,
    }

    result, success = run_alg(AddConfigurationStyleAlgorithm().name(), params)
    assert success
    assert result[AddConfigurationStyleAlgorithm.CREATED_ANNEXE_IDS] == ",".join(
        [created_annexe_id_1, created_annexe_id_2]
    )
