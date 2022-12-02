from r2gg._configure import configure
from r2gg._main import sql_convert, pgr_convert, osm_convert, osrm_convert, valhalla_convert, write_road2_config

__version__ = "1.2.2-DEVELOP"

def sql2pivot():
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)

def pivot2pgrouting():
    config, resource, db_configs, connection, logger = configure()
    pgr_convert(config, resource, db_configs, connection, logger)

def pivot2osm():
    config, resource, _, connection, logger = configure()
    osm_convert(config, resource, connection, logger)

def osm2osrm():
    config, resource, _, _, logger = configure()
    osrm_convert(config, resource, logger)

def osm2valhalla():
    config, resource, _, _, logger = configure()
    valhalla_convert(config, resource, logger)

def road2config():
    config, resource, _, _, logger = configure()
    write_road2_config(config, resource, logger)

if __name__ == '__main__':
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)
    if (resource['type'] in ['pgr', 'smartpgr']):
        config, resource, db_configs, connection, logger = configure()
        pgr_convert(config, resource, db_configs, connection, logger)
    elif (resource['type'] == 'osrm'):
        config, resource, db_configs, connection, logger = configure()
        osm_convert(config, resource, connection, logger)
        osrm_convert(config, resource, logger)
    elif (resource['type'] == 'valhalla'):
        config, resource, db_configs, connection, logger = configure()
        osm_convert(config, resource, connection, logger, True)
        valhalla_convert(config, resource, logger)
    else:
        raise ValueError("Wrong resource type, should be in ['pgr',osrm','valhalla','smartpgr']")
    write_road2_config(config, resource, logger)
