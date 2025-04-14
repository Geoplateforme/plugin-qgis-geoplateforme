#! python3

"""Script to generate the translation profile for a PyQt project, listing Python,
forms (ui) and targetted translation files. This script is intended to be run from the
root of the project, and will create a file named `plugin_translation.pro` in the
`geoplateforme/resources/i18n` directory.

TODO: remove the get_relative_paths function if your stack is Python 3.12+, which added
the walk_up option in pathlib.Path.relative_to(). It would be a cleaner solution.
Listing files would become:

    python_files = [
        f.relative_to(i18n_path, walk_up=True)
        for f in sorted(list(Path(src_path).rglob("*.py")))
        if not f.name.startswith("__")
    ]
    ui_files = [
        f.relative_to(i18n_path, walk_up=True)
        for f in sorted(list(Path(src_path).rglob("*.ui")))
    ]
    ts_files = [
        f.relative_to(i18n_path, walk_up=True)
        for f in sorted(list(Path(src_path).rglob("*.ts")))
    ]

So update the script accordingly by removing the function and references.
"""

# -- Imports
from os import path
from pathlib import Path

# -- Variables
src_path = Path("geoplateforme")
i18n_path = src_path.joinpath("resources/i18n")
output_file = i18n_path.joinpath("plugin_translation.pro")

# make sure the output directory exists
i18n_path.mkdir(parents=True, exist_ok=True)


# -- Functions
def get_relative_paths(filepaths_list: list[Path]) -> list[str]:
    """Parse a list of file paths and return a list of relative paths to the i18n
    directory, escaping the backslashes to make them compatible with Qt Linguist.

    :param filepaths_list: List of file paths to parse
    :type filepaths_list: list[Path]

    :return: List of relative paths to the i18n directory
    :rtype: list[str]
    """
    return [
        path.relpath(filepath, i18n_path).replace("\\", "/")
        for filepath in filepaths_list
    ]


# -- Run

# Get the list of all files in directory tree at given path
python_files = [
    f for f in sorted(list(Path(src_path).rglob("*.py"))) if not f.name.startswith("__")
]
ui_files = [f for f in sorted(list(Path(src_path).rglob("*.ui")))]
ts_files = [f for f in sorted(list(Path(src_path).rglob("*.ts")))]


# Generate the translation profile
forms = "FORMS =" + " \\\n".join([f"\t{f}" for f in get_relative_paths(ui_files)])

sources = "SOURCES =" + " \\\n".join(
    [f"\t{f}" for f in get_relative_paths(python_files)]
)

translations = "TRANSLATIONS =" + " \\\n".join(
    [f"\t{f}" for f in get_relative_paths(ts_files)]
)

# write to output file
with output_file.open("w", encoding="UTF-8") as f:
    f.write(
        "# This file is auto-generated by the script generate_translation_profile.py\n"
        "# Do not edit this file manually\n\n"
    )
    f.write(f"{forms}\n\n{sources}\n\n{translations}")
