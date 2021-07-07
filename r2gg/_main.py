import json
import multiprocessing
import os
import time
from datetime import datetime

import psycopg2
# https://github.com/andialbrecht/sqlparse
import sqlparse

from r2gg._lua_builder import build_lua
from r2gg._pivot_to_osm import pivot_to_osm
from r2gg._pivot_to_pgr import pivot_to_pgr
from r2gg._read_config import config_from_path
from r2gg._subprocess_exexution import subprocess_exexution
from r2gg._path_converter import convert_paths
from r2gg._file_copier import copy_files_locally,copy_files_with_ssh

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

    logger.info("Conversion from BDD to pivot")
    # Configuration de la bdd source
    source_db_config = db_configs[ resource['topology']['mapping']['source']['baseId'] ]

    # Configuration de la bdd de travail
    work_db_config = db_configs[ config['workingSpace']['baseId'] ]

    # Récupération de la bbox
    bbox = [float(coord) for coord in resource["topology"]["bbox"].split(",")]
    assert len(bbox) == 4, "bondingBox invalide"
    xmin = bbox[0]
    ymin = bbox[1]
    xmax = bbox[2]
    ymax = bbox[3]

    # Date de l'extraction pour la noter dans la configuration de la ressource
    extraction_date = datetime.now()
    # Ecriture dans un fichier temporaire de la date d'extraction
    work_dir_config = config['workingSpace']['directory']
    date_file = work_dir_config + "/r2gg.date"
    date_time = extraction_date.strftime("%m/%d/%Y")
    logger.info("extraction date to save in " + date_file + ": " + date_time)

    f = open(date_file, "w")
    f.write(date_time)
    f.close()

    st_sql_conversion = time.time()

    # Lancement du script SQL de conversion source --> pivot
    connection.autocommit = True
    with open( resource['topology']['mapping']['storage']['file'] ) as sql_script:
        cur = connection.cursor()
        logger.info("Executing SQL conversion script")
        instructions = sqlparse.split(sql_script.read().format(user=work_db_config.get('user')))

        # Exécution instruction par instruction
        for instruction in instructions:
            if instruction == '':
                continue
            logger.debug("SQL:\n{}\n".format(instruction) )
            st_instruction = time.time()
            cur.execute(instruction,
                {
                'bdpwd': source_db_config.get('password'), 'bdport': source_db_config.get('port'),
                'bdhost': source_db_config.get('host'), 'bduser': source_db_config.get('user'),
                'dbname': source_db_config.get('database'),
                'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax
                }
            )
            et_instruction = time.time()
            logger.info("Execution ended. Elapsed time : %s seconds." %(et_instruction - st_instruction))

    connection.close()

    et_sql_conversion = time.time()

    logger.info("Conversion from BDD to pivot ended. Elapsed time : %s seconds." %(et_sql_conversion - st_sql_conversion))

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
    logger.info("Conversion from pivot to PGR")
    st_pivot_to_pgr = time.time()

    # Configuration et connection à la base de sortie
    out_db_config = db_configs[ resource['topology']['storage']['baseId'] ]
    host = out_db_config.get('host')
    dbname = out_db_config.get('database')
    user = out_db_config.get('user')
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
    et_pivot_to_pgr = time.time()
    logger.info("Conversion from pivot to PGR ended. Elapsed time : %s seconds." %(et_pivot_to_pgr - st_pivot_to_pgr))
    _write_resource_file(config, resource, logger)


def osrm_convert(config, resource, db_configs, connection, logger, build_lua_from_cost_config = True):
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
    logger.info("Conversion from pivot to OSRM")

    logger.info("Conversion from pivot to OSM")
    pivot_to_osm(resource, connection, logger)
    connection.close()

    logger.info("Conversion from OSM to OSRM")
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
        start_command = time.time()
        subprocess_exexution(osrm_extract_args, logger)
        end_command = time.time()
        logger.info("OSRM extract ended. Elapsed time : %s seconds." %(end_command - start_command))
        subprocess_exexution(osrm_contract_args, logger)
        final_command = time.time()
        logger.info("OSRM contract ended. Elapsed time : %s seconds." %(final_command - end_command))
        subprocess_exexution(rm_args, logger)
        i += 1

    _write_resource_file(config, resource, logger)


def _write_resource_file(config, resource, logger, convert_file_paths = True, copy_files_out = False):
    """
    Fonction pour l'écriture du fichier de ressource

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    logger: logging.Logger
    """
    filename = config["outputs"]["configuration"]["storage"]["file"]
    logger.info("Writing resource file: " + filename)

    # Récupération de la date d'extraction
    work_dir_config = config['workingSpace']['directory']
    date_file = work_dir_config + "/r2gg.date"
    f = open(date_file, "r")
    extraction_date = f.read()
    logger.info("extraction date to add in resource (from "+ date_file +"): " + extraction_date)
    f.close()

    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)

    if convert_file_paths and config["outputs"].get("dirs", None) is not None:
        in_paths, out_paths = convert_paths(config, resource, config["outputs"]["dirs"])

    resource.pop("mapping", None)
    resource["topology"]["storage"].pop("baseId", None)
    for source in resource["sources"]:
        source["storage"].pop("dbConfig", None)

    resource["resourceVersion"] = extraction_date

    final_resource = {"resource": resource}
    with open(filename, "w") as resource_file:
        json_string = json.dumps(final_resource, indent=2)
        resource_file.write(json_string)

    if copy_files_out:
        copy_files_with_ssh(in_paths, out_paths, config["ssh_config"])
    else:
        copy_files_locally(in_paths, out_paths)
