#! python3  # noqa: E265

"""Metadata about the package to easily retrieve informations about it.

See: https://packaging.python.org/guides/single-sourcing-package-version/
"""

from datetime import date

__all__ = [
    "__author__",
    "__copyright__",
    "__email__",
    "__license__",
    "__summary__",
    "__title__",
    "__uri__",
    "__version__",
]

__author__ = "IGNF"
__copyright__ = "2022 - {0}, {1}".format(date.today().year, __author__)
__email__ = ""
__executable_name__ = "r2gg"
__package_name__ = "r2gg"

__keywords__ = ['cli', ' IGN', ' osrm', ' routing', ' pgrouting', ' valhalla', ' generation-algorithms', ' isochrone', ' road2']
__license__ = "GPL v3"
__summary__ = "Route Graph Generator (r2gg) est un script Python qui permet la génération de graphes pour des moteurs de calcul d'itinéraire"
__title__ = "Route Graph Generator"
__title_clean__ = "".join(e for e in __title__ if e.isalnum())
__uri_homepage__ = "https://ignf.github.io/route-graph-generator"
__uri_repository__ = "https://github.com/IGNF/route-graph-generator/"
__uri_tracker__ = f"{__uri_repository__}issues/"
__uri__ = __uri_repository__

__version__ = "2.2.4"
__version_info__ = tuple(
    [
        int(num) if num.isdigit() else num
        for num in __version__.replace("-", ".", 1).split(".")
    ]
)


__cli_usage__ = f"{__summary__}."
