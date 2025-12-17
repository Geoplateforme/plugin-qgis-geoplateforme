#! python3  # noqa E265

"""
Usage from the repo root folder:

.. code-block:: bash
    # for whole tests
    python -m unittest tests.unit.test_oauth2_configuration
    # for specific test
    python -m unittest tests.qgis.test_oauth2_configuration.TestOauth2Configuration.test_init_class
"""

# standard library
import unittest
from pathlib import Path

# project
from geoplateforme.datamodels.oauth2_configuration import OAuth2Configuration

# ############################################################################
# ########## Classes #############
# ################################


class TestOauth2Configuration(unittest.TestCase):
    """Test utils related to OAuth2Configuration."""

    def test_init_class(self):
        data = OAuth2Configuration()
        excepted = OAuth2Configuration(
            accessMethod=0,
            apiKey="",
            clientId="",
            clientSecret="",
            configType=1,
            customHeader="",
            description="Authentication related to the Géoplateforme plugin to give access to cartes.gouv.fr access your community, publish your data as services hosted on the IGN Geoplatform.",
            grantFlow=0,
            id="",
            name="geoplateforme_plugin_cfg",
            objectName="",
            password="",
            persistToken=True,
            queryPairs={},
            redirectPort=7070,
            redirectUrl="callback",
            refreshTokenUrl="",
            requestTimeout=30,
            requestUrl="https://sso.geopf.fr/realms/geoplateforme/protocol/openid-connect/auth",
            scope="",
            tokenUrl="https://sso.geopf.fr/realms/geoplateforme/protocol/openid-connect/token",
            username="",
            version=1,
        )
        self.assertEqual(data, excepted)

    def test_from_json_and_qgs_str_config(self):
        self.maxDiff = None
        # Test the from_json method
        json_config = Path("geoplateforme/auth/oauth2_config.json")
        self.assertTrue(json_config.exists)
        oauth_config = OAuth2Configuration.from_json(json_config)
        self.assertIsInstance(oauth_config, OAuth2Configuration)
        excepted = str(
            {
                "accessMethod": 0,
                "clientId": None,
                "clientSecret": None,
                "configType": 1,
                "grantFlow": 0,
                "persistToken": True,
                "redirectPort": 7070,
                "redirectUrl": "callback",
                "requestTimeout": 30,
                "requestUrl": "https://sso.geopf.fr/realms/geoplateforme/protocol/openid-connect/auth",
                "scope": "",
                "tokenUrl": "https://sso.geopf.fr/realms/geoplateforme/protocol/openid-connect/token",
                "version": 1,
            }
        )
        self.assertEqual(
            oauth_config.as_qgis_str_config_map(),
            excepted.replace("'", '"')
            .replace("True", "true")
            .replace("False", "false"),
        )
