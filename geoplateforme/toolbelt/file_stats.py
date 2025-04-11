#! python3  # noqa: E265

"""Check file statistcs."""

# ############################################################################
# ########## IMPORTS #############
# ################################

# standard library
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from math import floor
from math import log as math_log
from pathlib import Path
from sys import platform as opersys
from typing import Literal

# ############################################################################
# ########## GLOBALS #############
# ################################

# logs
logger = logging.getLogger(__name__)

# ############################################################################
# ########## FUNCTIONS ###########
# ################################


@lru_cache
def convert_octets(octets: int) -> str:
    """Convert a mount of octets in readable size.

    Args:
        octets: mount of octets to convert

    Returns:
        size in a human readable format: ko, Mo, etc.

    Example:

    .. code-block:: python

        >>> convert_octets(1024)
        1 ko
        >>> from pathlib import Path
        >>> convert_octets(Path(my_file.txt).stat().st_size)
    """
    # check zero
    if octets == 0:
        return "0 octet"

    # conversion
    size_name = ("octets", "Ko", "Mo", "Go", "To", "Po")
    i = int(floor(math_log(octets, 1024)))
    p = pow(1024, i)
    s = round(octets / p, 2)

    return f"{s} {size_name[i]}"


def is_file_older_than(
    local_file_path: Path,
    expiration_rotating_hours: int = 24,
    dt_reference_mode: Literal["auto", "creation", "modification"] = "auto",
) -> bool:
    """Check if the creation/modification date of the specified file is older than the \
        mount of hours.

    Args:
        local_file_path (Path): local path to the file
        expiration_rotating_hours (int, optional): number in hours to consider the \
            local file outdated. Defaults to 24.
        dt_reference_mode (Literal['auto', 'creation', 'modification'], optional):
            reference date type: auto to handle differences between operating systems,
            creation for creation date, modification for last modification date.
            Defaults to "auto".

    Returns:
        bool: True if the creation/modification date of the file is older than the \
            specified number of hours.
    """
    if not local_file_path.is_file() and not local_file_path.exists():
        logger.debug(f"{local_file_path} does not exist.")
        return True

    # modification date varies depending on operating system: on some systems (like
    # Unix) creation date is the time of the last metadata change, and, on others
    # (like Windows), is the creation time for path.
    if dt_reference_mode == "auto" and opersys == "win32":
        dt_reference_mode = "modification"
    else:
        dt_reference_mode = "creation"

    # get file reference datetime - modification or creation
    if dt_reference_mode == "modification":
        f_ref_dt = datetime.fromtimestamp(local_file_path.stat().st_mtime)
        dt_type = "modified"
    else:
        f_ref_dt = datetime.fromtimestamp(local_file_path.stat().st_ctime)
        dt_type = "created"

    if (datetime.now() - f_ref_dt) < timedelta(hours=expiration_rotating_hours):
        logger.debug(
            f"{local_file_path} has been {dt_type} less than "
            f"{expiration_rotating_hours} hours ago."
        )
        return False
    else:
        logger.debug(
            f"{local_file_path} has been {dt_type} more than "
            f"{expiration_rotating_hours} hours ago."
        )
        return True
