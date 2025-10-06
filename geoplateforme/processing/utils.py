import glob
import os
from pathlib import Path
from typing import List

# project
from geoplateforme.__about__ import __uri_homepage__


def tags_to_qgs_parameter_matrix_string(tags: dict[str, str]) -> str:
    """Convert a tags dict to a QgsProcessingParameterMatrix str

    :param tags: tags dict
    :type tags: dict[str, str]
    :return: QgsProcessingParameterMatrix string
    :rtype: str
    """
    return ";".join(f"{k},{v}" for k, v in tags.items())


def tags_from_qgs_parameter_matrix_string(matrix_row: list[str]) -> dict[str, str]:
    """Convert QgsProcessingParameterMatrix str to a tags dict

    :param matrix_row: QgsProcessingParameterMatrix string
    :type matrix_row: list[str]
    :return: tags dict
    :rtype: dict[str, str]
    """
    tag_values = [matrix_row[i : i + 2] for i in range(0, len(matrix_row), 2)]
    tags = {key: value for key, value in tag_values if key}
    return tags


def get_user_manual_url(processing_name: str) -> str:
    """Return url to user manual for a processing

    :param processing_name: processing name
    :type processing_name: str
    :return: user manual url
    :rtype: str
    """
    # Need to avoid use of _ in labels for Myst. Replacing with -
    fixed_processing_name = processing_name.replace("_", "-")
    return f"{__uri_homepage__}/usage/processings.html#{fixed_processing_name}"


def get_short_string(processing_name: str, default_help_str: str) -> str:
    """Get short string help for a processing.
    Use value defined in ../resources/help/processing_name.md if available.
    Otherwise, default_help_str is used

    :param processing_name: processing name
    :type processing_name: str
    :param default_help_str: default help string if no value available
    :type default_help_str: str
    :return: processing short string help
    :rtype: str
    """
    current_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    help_md = current_dir / ".." / "resources" / "help" / f"{processing_name}.md"
    help_str = default_help_str
    if os.path.exists(help_md):
        with open(help_md) as f:
            help_str = "".join(f.readlines())
    return help_str


def get_shapefile_associated_files(path: str) -> List[str]:
    """Get all file associated to a shapefile

    :param path: path to shapefile
    :type path: str
    :return: list of files for shapefile use
    :rtype: List[str]
    """
    base, _ = os.path.splitext(path)
    shp_associed_files = []
    for file in glob.glob(f"{base}.*"):
        if Path(file).suffix in [
            ".shx",
            ".dbf",
            ".prj",
            ".sbn",
            ".sbx",
            ".fbn",
            ".fbx",
            ".ain",
            ".aih",
            ".ixs",
            ".mxs",
            ".atx",
            ".cpg",
            ".qix",
        ]:
            shp_associed_files.append(file)
    return shp_associed_files
