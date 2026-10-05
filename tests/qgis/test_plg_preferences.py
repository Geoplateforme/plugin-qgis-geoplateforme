#! python3

"""
Usage from the repo root folder:

.. code-block:: bash

    # for whole tests
    python -m unittest tests.qgis.test_plg_preferences
    # for specific test
    python -m unittest tests.qgis.test_plg_preferences.TestPlgPreferences.test_plg_preferences_structure
"""

# standard library
import os
from unittest.mock import patch

# PyQGIS
from qgis.testing import unittest

# project
from geoplateforme.__about__ import __version__
from geoplateforme.toolbelt.preferences import (
    PREFIX_ENV_VARIABLE,
    PlgOptionsManager,
    PlgSettingsStructure,
)

# ############################################################################
# ########## Classes #############
# ################################


class TestPlgPreferences(unittest.TestCase):
    def test_plg_preferences_structure(self):
        """Test settings types and default values."""
        settings = PlgSettingsStructure()

        # global
        self.assertTrue(hasattr(settings, "debug_mode"))
        self.assertIsInstance(settings.debug_mode, bool)
        self.assertFalse(settings.debug_mode)

        self.assertTrue(hasattr(settings, "version"))
        self.assertIsInstance(settings.version, str)
        self.assertEqual(settings.version, __version__)

        # network and authentication
        self.assertTrue(hasattr(settings, "url_geoplateforme"))
        self.assertIsInstance(settings.url_geoplateforme, str)
        self.assertEqual(settings.url_geoplateforme, "https://cartes.gouv.fr/")

        self.assertTrue(hasattr(settings, "url_api_entrepot"))
        self.assertIsInstance(settings.url_api_entrepot, str)
        self.assertEqual(settings.url_api_entrepot, "https://data.geopf.fr/api")

        self.assertTrue(hasattr(settings, "qgis_auth_id"))
        self.assertIsNone(settings.qgis_auth_id, None)

    def test_bool_env_variable(self):
        """Test settings with environment value."""
        manager = PlgOptionsManager()
        with patch.dict(
            os.environ, {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "true"}, clear=True
        ):
            settings = manager.get_plg_settings()
            self.assertTrue(settings.debug_mode)

        with patch.dict(
            os.environ, {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "false"}, clear=True
        ):
            settings = manager.get_plg_settings()
            self.assertFalse(settings.debug_mode)

        with patch.dict(
            os.environ, {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "on"}, clear=True
        ):
            settings = manager.get_plg_settings()
            self.assertTrue(settings.debug_mode)

        with patch.dict(
            os.environ, {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "off"}, clear=True
        ):
            settings = manager.get_plg_settings()
            self.assertFalse(settings.debug_mode)

        with patch.dict(
            os.environ, {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "1"}, clear=True
        ):
            settings = manager.get_plg_settings()
            self.assertTrue(settings.debug_mode)

        with patch.dict(
            os.environ, {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "0"}, clear=True
        ):
            settings = manager.get_plg_settings()
            self.assertFalse(settings.debug_mode)

        with patch.dict(
            os.environ,
            {f"{PREFIX_ENV_VARIABLE}DEBUG_MODE": "invalid_value"},
            clear=True,
        ):
            settings = manager.get_plg_settings()
            self.assertFalse(settings.debug_mode)


# ############################################################################
# ####### Stand-alone run ########
# ################################
if __name__ == "__main__":
    unittest.main()
