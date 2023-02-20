#! python3  # noqa: E265

"""Main CLI entrypoint."""

# Package
from r2gg.__about__ import (
    __author__,
    __cli_usage__,
    __summary__,
    __title__,
    __title_clean__,
    __uri_homepage__,
    __version__,
)
from r2gg._configure import configure
from r2gg._main import sql_convert, pgr_convert, osm_convert, osrm_convert, valhalla_convert, write_road2_config

# ############################################################################
# ########## MAIN ################
# ################################
def sql2pivot():
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)

def pivot2pgrouting():
    config, resource, db_configs, connection, logger = configure()
    pgr_convert(config, resource, db_configs, connection, logger)

def pivot2osm():
    config, resource, db_configs, connection, logger = configure()
    osm_convert(config, resource, db_configs, connection, logger)

def osm2osrm():
    config, resource, _, _, logger = configure()
    osrm_convert(config, resource, logger)

def osm2valhalla():
    config, resource, _, _, logger = configure()
    valhalla_convert(config, resource, logger)

def road2config():
    config, resource, _, _, logger = configure()
    write_road2_config(config, resource, logger)

def main():
    """Main CLI entrypoint.
    """
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)
    if (resource['type'] in ['pgr', 'smartpgr']):
        config, resource, db_configs, connection, logger = configure()
        pgr_convert(config, resource, db_configs, connection, logger)
    elif (resource['type'] == 'osrm'):
        config, resource, db_configs, connection, logger = configure()
        osm_convert(config, resource, db_configs,  connection, logger)
        osrm_convert(config, resource, logger)
    elif (resource['type'] == 'valhalla'):
        config, resource, db_configs, connection, logger = configure()
        osm_convert(config, resource, db_configs, connection, logger, True)
        valhalla_convert(config, resource, logger)
    else:
        raise ValueError("Wrong resource type, should be in ['pgr',osrm','valhalla','smartpgr']")
    write_road2_config(config, resource, logger)

# -- Stand alone execution
if __name__ == "__main__":
    main()  # required by unittest
