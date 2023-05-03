#! python3  # noqa: E265

"""Setup script to package into a Python module."""

# ############################################################################
# ########## Libraries #############
# ##################################

# standard library
from pathlib import Path

# 3rd party
from setuptools import find_packages, setup

# package (to get version)
from r2gg import __about__

# ############################################################################
# ########### Globals ##############
# ##################################

# The directory containing this file
HERE = Path(__file__).parent

requirements = []
with open(HERE / "requirements/base.txt") as f:
    requirements = [
        line
        for line in f.read().splitlines()
        if not line.startswith(("#", "-")) and len(line)
    ]

# The text of the README file
README = (HERE / "README.md").read_text()

# ############################################################################
# ########### Main #################
# ##################################

setup(
    name=__about__.__package_name__,
    author=__about__.__author__,
    author_email=__about__.__email__,
    description=__about__.__summary__,
    long_description=README,
    long_description_content_type="text/markdown",
    keywords=__about__.__keywords__,
    url=__about__.__uri__,
    version=__about__.__version__,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    # packaging
    packages=find_packages(
        exclude=["contrib", "docs", "*.tests", "*.tests.*", "tests.*", "tests", ".venv"]
    ),
    include_package_data=True,
    install_requires=requirements,

    # cli
    entry_points={
        "console_scripts": [
            f"{__about__.__executable_name__} = r2gg.cli:main",
            f"{__about__.__executable_name__}-sql2pivot = r2gg.cli:sql2pivot",
            f"{__about__.__executable_name__}-pivot2pgrouting = r2gg.cli:pivot2pgrouting",
            f"{__about__.__executable_name__}-pivot2osm = r2gg.cli:pivot2osm",
            f"{__about__.__executable_name__}-osm2osrm = r2gg.cli:osm2osrm",
            f"{__about__.__executable_name__}-osm2valhalla = r2gg.cli:osm2valhalla",
            f"{__about__.__executable_name__}-road2config = r2gg.cli:road2config"
        ]
    },
)
