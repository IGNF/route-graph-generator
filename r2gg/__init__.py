from r2gg._configure import configure
from r2gg._main import sql_convert, pgr_convert, osrm_convert

__version__ = "1.0.02-DEVELOP"

def populate_pivot():
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)

def pivot2pgrouting():
    config, resource, db_configs, connection, logger = configure()
    pgr_convert(config, resource, db_configs, connection, logger)

def pivot2osrm():
    config, resource, db_configs, connection, logger = configure()
    osrm_convert(config, resource, db_configs, connection, logger)

if __name__ == '__main__':
    config, resource, db_configs, connection, logger = configure()
    sql_convert(config, resource, db_configs, connection, logger)
    if (resource['type'] == 'pgr'):
        config, resource, db_configs, connection, logger = configure()
        pgr_convert(config, resource, db_configs, connection, logger)
    elif (resource['type'] == 'osrm'):
        config, resource, db_configs, connection, logger = configure()
        osrm_convert(config, resource, db_configs, connection, logger)
    else:
        raise ValueError("Wrong resource type, should be 'pgr' or osrm'")
