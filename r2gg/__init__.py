from r2gg._configure import configure
from r2gg._main import sql_convert, pgr_convert, osm_convert, osrm_convert

__version__ = "1.1.0-DEVELOP"

def populate_pivot():
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)

def pivot2pgrouting():
    config, resource, db_configs, connection, logger = configure()
    pgr_convert(config, resource, db_configs, connection, logger)

def pivot2osm():
    _, resource, _, connection, logger = configure()
    osm_convert(resource, connection, logger)

def osm2osrm():
    config, resource, _, _, logger = configure()
    osrm_convert(config, resource, logger)


if __name__ == '__main__':
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)
    if (resource['type'] in ['pgr', 'smartpgr']):
        config, resource, db_configs, connection, logger = configure()
        pgr_convert(config, resource, db_configs, connection, logger)
    elif (resource['type'] == 'osrm'):
        config, resource, db_configs, connection, logger = configure()
        osm_convert(config, resource, db_configs, connection, logger)
        osrm_convert(config, resource, db_configs, connection, logger)
    else:
        raise ValueError("Wrong resource type, should be 'pgr' or osrm'")
