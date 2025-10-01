#! python3  # noqa: E265

"""Main CLI entrypoint."""

# Package
from r2gg._configure import configure
from r2gg._main import sql_convert, pgr_convert, osm_convert, osrm_convert, valhalla_convert, write_road2_config
from r2gg._database import DatabaseManager

# ############################################################################
# ########## MAIN ################
# ################################
def sql2pivot():
    config, resource, db_configs, logger = configure()
    database = DatabaseManager(db_configs[config["workingSpace"]["baseId"]], logger)
    sql_convert(config, resource, db_configs, database, logger)
    database.disconnect_working_db()

def pivot2pgrouting():
    config, resource, db_configs, logger = configure()
    database = DatabaseManager(db_configs[config["workingSpace"]["baseId"]], logger)
    pgr_convert(resource, db_configs, database, logger)
    database.disconnect_working_db()

def pivot2osm():
    config, resource, db_configs, logger = configure()
    database = DatabaseManager(db_configs[config["workingSpace"]["baseId"]], logger)
    osm_convert(config, resource, db_configs, database, logger)
    database.disconnect_working_db()

def osm2osrm():
    config, resource, _, logger = configure()
    osrm_convert(config, resource, logger)

def osm2valhalla():
    config, resource, _, logger = configure()
    valhalla_convert(config, resource, logger)

def road2config():
    config, resource, _, logger = configure()
    write_road2_config(config, resource, logger)

def main():
    """Main CLI entrypoint.
    """
    config, resource, db_configs, logger = configure()
    sql2pivot()
    if resource['type'] in ['pgr', 'smartpgr']:
        pivot2pgrouting()
    elif resource['type'] == 'osrm':
        pivot2osm()
        osrm_convert(config, resource, logger)
    elif resource['type'] == 'valhalla':
        pivot2osm()
        valhalla_convert(config, resource, logger)
    else:
        raise ValueError("Wrong resource type, should be in ['pgr',osrm','valhalla','smartpgr']")
    write_road2_config(config, resource, logger)

# -- Stand alone execution
if __name__ == "__main__":
    main()  # required by unittest
