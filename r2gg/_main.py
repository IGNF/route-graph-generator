import json
import multiprocessing
import os

import psycopg2
# https://github.com/andialbrecht/sqlparse
import sqlparse

from r2gg._pivot_to_osm import pivot_to_osm
from r2gg._pivot_to_pgr import pivot_to_pgr
from r2gg._subprocess_exexution import subprocess_exexution

def sql_convert(config, resource, db_configs, connection, logger):
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
    connection.close()

def pgr_convert(config, resource, db_configs, connection, logger):
    if (resource['type'] != 'pgr'):
        raise ValueError("Wrong resource type, should be 'pgr'")

    # Configuration et connection à la base de sortie
    out_db_config = db_configs[ resource['topology']['storage']['baseId'] ]
    host = out_db_config.get('host')
    dbname = out_db_config.get('dbname')
    user = out_db_config.get('username')
    password = out_db_config.get('password')
    port = out_db_config.get('port')
    connect_args = 'host=%s dbname=%s user=%s password=%s port=%s' %(host, dbname, user, password, port)
    logger.info("Connecting to output database")
    connection_out = psycopg2.connect(connect_args)

    pivot_to_pgr(resource, connection, connection_out, logger)
    connection.close()
    connection_out.close()
    # Écriture du fichier resource TODO: n'écrire que le nécessaire
    logger.info("Writing resource file")
    filename = resource["outputs"]["configuration"]["storage"]["file"]

    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
    with open(filename, "w") as resource_file:
        json_string = json.dumps(resource, indent=2)
        resource_file.write(json_string)

def osrm_convert(config, resource, db_configs, connection, logger):
    if (resource['type'] != 'osrm'):
        raise ValueError("Wrong resource type, should be 'osrm'")

    pivot_to_osm(resource, connection, logger)
    connection.close()

    # osm2osrm
    osm_file = resource['topology']['storage']['file']
    logger.info("Generating graphs for each cost...")
    cpu_count = multiprocessing.cpu_count()

    for i in range(len(resource["sources"])):
        logger.info("Source {} of {}...".format(i+1, len(resource["sources"])))
        lua_file = resource["sources"][i]["cost"]["compute"]["storage"]["file"]
        # Gestion des points "." dans le chemin d'accès avec ".".join()
        osrm_file = resource["sources"][i]["storage"]["file"]
        cost_dir = os.path.dirname(osrm_file)
        cost_name = cost_dir.split("/")[-1]
        tmp_osm_file = "{}/{}.osm".format(cost_dir, cost_name)

        # Définition des commandes shell à exécuter
        mkdir_args = ["mkdir", "-p", cost_dir]
        copy_args = ["cp", ".".join(osm_file.split(".")[:-1]) + ".osm", tmp_osm_file]
        osrm_extract_args = ["osrm-extract", tmp_osm_file, "-p", lua_file, "-t", cpu_count]
        osrm_contract_args = ["osrm-contract", osrm_file, "-t", cpu_count]
        rm_args = ["rm", tmp_osm_file]

        subprocess_exexution(mkdir_args, logger)
        subprocess_exexution(copy_args, logger)
        subprocess_exexution(osrm_extract_args, logger)
        subprocess_exexution(osrm_contract_args, logger)
        subprocess_exexution(rm_args, logger)

    # Écriture du fichier resource TODO: n'écrire que le nécessaire
    logger.info("Writing resource file")
    filename = config["outputs"]["configuration"]["storage"]["file"]

    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
    final_resource = {"resource": resource}
    with open(filename, "w") as resource_file:
        json_string = json.dumps(final_resource, indent=2)
        resource_file.write(json_string)
