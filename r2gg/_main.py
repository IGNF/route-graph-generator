
import psycopg2
# https://github.com/andialbrecht/sqlparse
import sqlparse

from _pivot_to_osm import pivot_to_osm
from _pivot_to_pgr import pivot_to_pgr

def execute(config, resource, db_configs, connection, logger):
    # Configuration de la bdd source
    source_db_config = db_configs[ resource['topology']['mapping']['source']['baseId'] ]

    # Configuration de la bdd de travail
    work_db_config = db_configs[ config['workingSpace']['baseId'] ]

    # Lancement du script SQL de conversion source --> pivot
    with open( resource['topology']['mapping']['storage']['file'] ) as sql_script:
        cur = connection.cursor()
        logger.info("Executing SQL conversion script")
        instructions = sqlparse.split(sql_script.read().format(user=work_db_config.get('username')))

        # Exécution instruction par instruction
        for instruction in instructions:
            if instruction == '':
                continue
            logger.debug("SQL:\n {}\n".format(instruction) )
            cur.execute(instruction,
                {'bdpwd': source_db_config.get('password'), 'bdport': source_db_config.get('port'),
                'bdhost': source_db_config.get('host'), 'bduser': source_db_config.get('username'),
                'dbname': source_db_config.get('dbname')
                })
        connection.commit()

    # Si la sortie est de type pgrouting
    if (resource['type'] == 'pgr'):
        # Configuration et connection à la base de sortie
        out_db_config = db_configs[ resource['topology']['storage']['baseId'] ]
        host = out_db_config.get('host')
        dbname = out_db_config.get('dbname')
        user = out_db_config.get('username')
        password = out_db_config.get('password')
        port = out_db_config.get('port')
        connect_args = 'host=%s dbname=%s user=%s password=%s' %(host, dbname, user, password)
        logger.info("Connecting to output database")
        connection_out = psycopg2.connect(connect_args)

        pivot_to_pgr(resource, connection, connection_out, logger)
        connection.close()
        connection_out.close()

    elif (resource['type'] == 'osrm' or resource['type'] == 'osm'):

        pivot_to_osm(resource, connection, logger)
        connection.close()

        if (resource['type'] == 'osrm'):
            # TODO: use lua scripts
            pass
    else:
        raise ValueError("Wrong resource type, should be one of (pgr, osm, orsm)")
