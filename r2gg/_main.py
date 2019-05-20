import json
import multiprocessing
import os

import psycopg2
# https://github.com/andialbrecht/sqlparse
import sqlparse

from r2gg._lua_builder import build_lua
from r2gg._pivot_to_osm import pivot_to_osm
from r2gg._pivot_to_pgr import pivot_to_pgr
from r2gg._read_config import config_from_path
from r2gg._subprocess_exexution import subprocess_exexution

def sql_convert(config, resource, db_configs, connection, logger):
    """
    Fonction de conversion depuis la bdd source vers la bdd pivot

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    db_configs: dict
        dictionnaire correspondant aux configurations des bdd
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """

    # Configuration de la bdd source
    source_db_config = db_configs[ resource['topology']['mapping']['source']['baseId'] ]

    # Configuration de la bdd de travail
    work_db_config = db_configs[ config['workingSpace']['baseId'] ]

    # Récupération de la bbox
    bbox = [float(coord) for coord in resource["boundingBox"].split(",")]
    assert len(bbox) == 4, "bondingBox invalide"
    xmin = bbox[0]
    ymin = bbox[1]
    xmax = bbox[2]
    ymax = bbox[3]

    # Lancement du script SQL de conversion source --> pivot
    with open( resource['topology']['mapping']['storage']['file'] ) as sql_script:
        cur = connection.cursor()
        logger.info("Executing SQL conversion script")
        instructions = sqlparse.split(sql_script.read().format(user=work_db_config.get('username')))

        # Exécution instruction par instruction
        for instruction in instructions:
            if instruction == '':
                continue
            logger.debug("SQL:\n{}\n".format(instruction) )
            cur.execute(instruction,
                {
                  'bdpwd': source_db_config.get('password'), 'bdport': source_db_config.get('port'),
                  'bdhost': source_db_config.get('host'), 'bduser': source_db_config.get('username'),
                  'dbname': source_db_config.get('dbname'),
                  'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax
                }
            )
        connection.commit()
    connection.close()

def pgr_convert(config, resource, db_configs, connection, logger):
    """
    Fonction de conversion depuis la bdd pivot vers la bdd pgrouting

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    db_configs: dict
        dictionnaire correspondant aux configurations des bdd
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """

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

    cost_calculation_files_paths = {source["cost"]["compute"]["storage"]["file"] for source in resource["sources"]}

    for cost_calculation_file_path in cost_calculation_files_paths:
        pivot_to_pgr(resource, cost_calculation_file_path, connection, connection_out, logger)

    connection.close()
    connection_out.close()
    # Écriture du fichier resource TODO: n'écrire que le nécessaire
    logger.info("Writing resource file")
    filename = config["outputs"]["configuration"]["storage"]["file"]

    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
    with open(filename, "w") as resource_file:
        json_string = json.dumps(resource, indent=2)
        resource_file.write(json_string)

def osrm_convert(config, resource, db_configs, connection, logger, build_lua_from_cost_config = False):
    """
    Fonction de conversion depuis la bdd pivot vers les fichiers osm et osrm

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    db_configs: dict
        dictionnaire correspondant aux configurations des bdd
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """

    if (resource['type'] != 'osrm'):
        raise ValueError("Wrong resource type, should be 'osrm'")

    pivot_to_osm(resource, connection, logger)
    connection.close()

    # osm2osrm
    osm_file = resource['topology']['storage']['file']
    logger.info("Generating graphs for each cost...")
    cpu_count = multiprocessing.cpu_count()

    i = 0
    for source in resource["sources"]:
        logger.info("Source {} of {}...".format(i+1, len(resource["sources"])))
        lua_file = source["cost"]["compute"]["storage"]["file"]

        if build_lua_from_cost_config:
            logger.info("Building lua profile")
            config_file = source["cost"]["compute"]["configuration"]["storage"]["file"]
            costs_config = config_from_path(config_file)
            cost_name = source["cost"]["compute"]["configuration"]["name"]

            if cost_name not in [ output["name"] for output in costs_config["outputs"] ]:
                raise ValueError("cost_name must be in cost configuration")

            with open(lua_file, "w") as lua_f:
                lua_f.write(build_lua(costs_config, cost_name))
            logger.info("Finished lua building")

        # Gestion des points "." dans le chemin d'accès avec ".".join()
        osrm_file = source["storage"]["file"]
        cost_dir = os.path.dirname(osrm_file)
        profile_name = osrm_file.split("/")[-1].split(".")[0]
        tmp_osm_file = "{}/{}.osm".format(cost_dir, profile_name)

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
        i += 1

    # Écriture du fichier resource TODO: n'écrire que le nécessaire
    logger.info("Writing resource file")
    filename = config["outputs"]["configuration"]["storage"]["file"]

    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
    final_resource = {"resource": resource}
    with open(filename, "w") as resource_file:
        json_string = json.dumps(final_resource, indent=2)
        resource_file.write(json_string)
