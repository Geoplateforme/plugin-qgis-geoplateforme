# standard
import json
import math
import re
from typing import List

# PyQGIS
from qgis.PyQt.QtCore import QUrl

# plugin
from geoplateforme.api.custom_exceptions import ReadCommunityException
from geoplateforme.api.user import Community
from geoplateforme.toolbelt import NetworkRequestsManager, PlgLogger, PlgOptionsManager


class CatalogRequestManager:
    MAX_LIMIT = 50

    def get_base_url(self) -> str:
        """Get base url for communitys

        :return: url for communitys
        :rtype: str
        """

        return f"{self.plg_settings.base_url_api_entrepot}/catalogs"

    def __init__(self):
        """Helper for catalog request"""
        self.log = PlgLogger().log
        self.request_manager = NetworkRequestsManager()
        self.plg_settings = PlgOptionsManager.get_plg_settings()

    def get_community_list(self) -> List[Community]:
        """Get list of community

        :raises ReadCommunityException: when error occur during requesting the API

        :return: list of available community
        :rtype: List[Community]
        """
        self.log(f"{__name__}.get_community_list()")

        nb_value = self._get_nb_available_community()
        nb_request = math.ceil(nb_value / self.MAX_LIMIT)
        result = []
        for page in range(0, nb_request):
            result += self._get_community_list(page + 1, self.MAX_LIMIT)
        return result

    def _get_community_list(
        self,
        page: int = 1,
        limit: int = MAX_LIMIT,
    ) -> List[Community]:
        """Get list of community

        :param page: page number (start at 1)
        :type page: int
        :param limit: nb response per pages
        :type limit: int

        :raises ReadCommunityException: when error occur during requesting the API

        :return: list of available community
        :rtype: List[Community]
        """
        try:
            reply = self.request_manager.get_url(
                url=QUrl(
                    f"{self.get_base_url()}/communities?page={page}&limit={limit}"
                ),
                config_id=self.plg_settings.qgis_auth_id,
            )
        except ConnectionError as err:
            raise ReadCommunityException(
                f"Error while fetching catalog community : {err}"
            )

        data = json.loads(reply.data())
        return [Community.from_dict(val) for val in data]

    def _get_nb_available_community(
        self,
    ) -> int:
        """Get number of available community

        :raises ReadCommunityException: when error occur during requesting the API

        :return: number of available data
        :rtype: int
        """
        # For now read with maximum limit possible
        try:
            req_reply = self.request_manager.get_url(
                url=QUrl(f"{self.get_base_url()}/communities?limit=1"),
                config_id=self.plg_settings.qgis_auth_id,
                return_req_reply=True,
            )
        except ConnectionError as err:
            raise ReadCommunityException(
                f"Error while fetching catalog community : {err}"
            )

        # check response
        content_range = req_reply.rawHeader(b"Content-Range").data().decode("utf-8")
        match = re.match(
            r"(?P<min>\d+)\s?-\s?(?P<max>\d+)?\s?\/?\s?(?P<nb_val>\d+|\*)?",
            content_range,
        )
        if match:
            nb_val = int(match.group("nb_val"))
        else:
            raise ReadCommunityException(
                f"Invalid Content-Range {content_range} not min-max/nb_val as expected"
            )
        return nb_val
