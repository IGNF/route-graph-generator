import argparse
import json
import os
from pathlib import Path
from urllib import request

# 3rd party
import pytest
from unittest.mock import patch

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from r2gg import cli

import psycopg2 as psycopg

cur_dir = Path(__file__).parent.absolute()

# ############################################################################
# ########## Classes #############
# ################################
HOST = os.environ.get("POSTGRES_HOST", "172.17.0.1")
PORT = os.environ.get("PORT", 5555)
DBNAME = os.environ.get("POSTGRES_DB", "ign")
USER = os.environ.get("POSTGRES_USER", "ign")
PASS = os.environ.get("POSTGRES_PASSWORD", "ign")

# Schemas are defined in input configuration .json files
INPUT_SCHEMA = "input"
OUTPUT_SCHEMA = "output"

TRONCON_ROUTE_URL = "https://storage.gra.cloud.ovh.net/v1/AUTH_366279ce616242ebb14161b7991a8461/road2/troncon_route_marseille10.sql"
NON_COMMUNICATION_URL = "https://storage.gra.cloud.ovh.net/v1/AUTH_366279ce616242ebb14161b7991a8461/road2/non_communication_marseille10.sql"

@pytest.fixture
def init_database(tmp_path) -> None:
    """Init database for test."""

    con = psycopg.connect(host=HOST, dbname=DBNAME, user=USER, password=PASS, port=PORT)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    con.cursor().execute(f"CREATE SCHEMA IF NOT EXISTS {INPUT_SCHEMA}")
    con.cursor().execute(f"CREATE DATABASE pivot")
    con.commit()
    con.close()

    # Insert test data
    con = psycopg.connect(host=HOST, dbname=DBNAME, user=USER, password=PASS, port=PORT)
    cur = con.cursor()
    cur.execute(f"SET search_path TO {INPUT_SCHEMA}")

    request.urlretrieve(TRONCON_ROUTE_URL, tmp_path / "troncon_route_marseille10.sql")
    request.urlretrieve(NON_COMMUNICATION_URL, tmp_path / "non_communication_marseille10.sql")

    with open(str(tmp_path / "troncon_route_marseille10.sql"), mode="r") as sql_script:
        cur.execute(sql_script.read())
    with open(str(tmp_path / "non_communication_marseille10.sql"), mode="r") as sql_script:
        cur.execute(sql_script.read())

    con.commit()
    con.close()

    # Add extensions to pivot
    con = psycopg.connect(host=HOST, dbname="pivot", user=USER, password=PASS, port=PORT)
    con.cursor().execute(f"CREATE SCHEMA IF NOT EXISTS {OUTPUT_SCHEMA}")
    con.cursor().execute("CREATE EXTENSION IF NOT EXISTS postgres_fdw")
    con.cursor().execute("CREATE EXTENSION IF NOT EXISTS Postgis")
    con.commit()
    con.close()
    yield

    con = psycopg.connect(host=HOST, dbname=DBNAME, user=USER, password=PASS, port=PORT)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    con.cursor().execute("DROP DATABASE pivot")
    con.cursor().execute(f"DROP TABLE {INPUT_SCHEMA}.non_communication")
    con.cursor().execute(f"DROP TABLE {INPUT_SCHEMA}.troncon_de_route")
    con.commit()
    con.close()


def update_src_dir_json(file_path: Path, output_file_path: Path):
    """Update .json file to replace {src_dir} by current source directory

    Parameters
    ----------
    file_path (Path) database .json file path
    """
    with open(file_path, mode="r") as f:
        content = f.read().replace("{src_dir}", str(Path(cur_dir / "..").resolve()))

    with open(output_file_path, mode="w") as f:
        f.write(content)


def sql2pivot():
    """Simple run of cli for pivot base creation."""
    # Update input json file to indicate current source directory
    update_src_dir_json(cur_dir / "config" / "sql2pivot.json", cur_dir / "config" / "updated_sql2pivot.json")

    # mock ArgumentParser for configuration file
    with patch("argparse.ArgumentParser.parse_args") as parse_arg_mock:
        parse_arg_mock.return_value = argparse.Namespace(
            config_file_path=str(cur_dir / "config" / "updated_sql2pivot.json"))
        # Run conversion
        cli.sql2pivot()


def test_sql2pivot(init_database):
    """Test simple run of cli for pivot base creation."""
    sql2pivot()


def pivot2osm():
    """Simple run of cli for osm file creation from pivot database."""
    # Update input json file to indicate current source directory
    update_src_dir_json(cur_dir / "config" / "pivot2osm.json", cur_dir / "config" / "updated_pivot2osm.json")

    # mock ArgumentParser for configuration file
    with patch("argparse.ArgumentParser.parse_args") as parse_arg_mock:
        parse_arg_mock.return_value = argparse.Namespace(
            config_file_path=str(cur_dir / "config" / "updated_pivot2osm.json"))
        # Run conversion
        cli.pivot2osm()

        assert os.path.exists("/home/docker/data/generation/pivot-osm.osm")


def test_pivot2osm(init_database):
    """Test simple run of cli for osm file creation from pivot database."""

    sql2pivot()
    pivot2osm()

