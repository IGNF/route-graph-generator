import json
import multiprocessing
import os
import json
import time
from datetime import datetime

import psycopg2
# https://github.com/andialbrecht/sqlparse
import sqlparse

from r2gg._lua_builder import build_lua
from r2gg._pivot_to_osm import pivot_to_osm
from r2gg._pivot_to_pgr import pivot_to_pgr
from r2gg._read_config import config_from_path
from r2gg._subprocess_execution import subprocess_execution
from r2gg._path_converter import convert_path
from r2gg._file_copier import copy_file_locally
from r2gg._valhalla_lua_builder import build_valhalla_lua
from r2gg._osm_to_pbf import osm_to_pbf


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

    # Date de l'extraction pour la noter dans la configuration de la ressource
    extraction_date = datetime.now()
    # Ecriture dans un fichier temporaire de la date d'extraction
    work_dir_config = config['workingSpace']['directory']
    date_file = os.path.join(work_dir_config, "r2gg.date")
    date_time = extraction_date.strftime("%Y-%m-%d")
    logger.info("extraction date to save in " + date_file + ": " + date_time)

    f = open(date_file, "w")
    f.write(date_time)
    f.close()

    # Mesure du temps de l'ensemble des génération pivot
    st_sql_conversion = time.time()

    used_bases = []

    # Il y a potentiellement une conversion par source indiquée dans la ressource
    for source in resource[ 'sources' ]:

        logger.info("Create pivot of source: " + source['id'])

        # Les sources smartrouting n'ont pas besoin de génération mais peuvent apparaître dans certaines ressources
        if source['type'] == 'smartrouting':
            logger.info("Smartrouting source, no need for pivot")
            continue

        # Plusieurs sources peuvent référencer le même mapping mais changer plus tard dans la génération
        found_base = False
        for ub in used_bases:
            if ub == source['mapping']['source']['baseId']:
                found_base = True
        if found_base:
            logger.info("Mapping already done, create next source...")
            continue
        else:
            logger.info("Mapping not done")

        # Configuration de la bdd source
        source_db_config = db_configs[ source['mapping']['source']['baseId'] ]
        used_bases.append(source['mapping']['source']['baseId'])

        # Configuration de la bdd de travail utilisée pour ce pivot
        work_db_config = db_configs[ config['workingSpace']['baseId'] ]

        # Récupération de la bbox
        bbox = [float(coord) for coord in source["bbox"].split(",")]
        assert len(bbox) == 4, "bondingBox invalide"
        xmin = bbox[0]
        ymin = bbox[1]
        xmax = bbox[2]
        ymax = bbox[3]
        logger.info("Create source on bbox: " + source["bbox"])

        # Lancement du script SQL de conversion source --> pivot
        connection.autocommit = True
        with open( source['mapping']['conversion']['file'] ) as sql_script:
            cur = connection.cursor()
            logger.info("Executing SQL conversion script")
            instructions = sqlparse.split(sql_script.read().format(user=work_db_config.get('user'),
                                                                   input_schema=source_db_config.get('schema'),
                                                                   output_schema=work_db_config.get('schema')
                                                                   ))

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

    if (resource['type'] not in ['pgr', 'smartpgr']):
        raise ValueError("Wrong resource type, should be 'pgr' or 'smartpgr'")

    logger.info("Conversion from pivot to PGR")
    st_pivot_to_pgr = time.time()

    i = 0
    for source in resource["sources"]:

        logger.info("Source {} of {}...".format(i+1, len(resource["sources"])))
        logger.info("Source id : " + source["id"])

        # Configuration et connection à la base de sortie
        out_db_config = db_configs[ source['storage']['base']['baseId'] ]
        host = out_db_config.get('host')
        dbname = out_db_config.get('database')
        user = out_db_config.get('user')
        password = out_db_config.get('password')
        port = out_db_config.get('port')
        connect_args = 'host=%s dbname=%s user=%s password=%s port=%s' %(host, dbname, user, password, port)
        logger.info("Connecting to output database")
        connection_out = psycopg2.connect(connect_args)

        schema_out = out_db_config.get('schema')

        source_db_config = db_configs[source['mapping']['source']['baseId']]
        input_schema = source_db_config.get('schema')

        cost_calculation_files_paths = {cost["compute"]["configuration"]["storage"]["file"] for cost in source["costs"]}

        for cost_calculation_file_path in cost_calculation_files_paths:
            pivot_to_pgr(source, cost_calculation_file_path, connection, connection_out, schema_out, input_schema, logger)
        connection_out.close()

    et_pivot_to_pgr = time.time()
    logger.info("Conversion from pivot to PGR ended. Elapsed time : %s seconds." %(et_pivot_to_pgr - st_pivot_to_pgr))


def osm_convert(config, resource, db_configs, connection, logger):
    """
    Fonction de conversion depuis la bdd pivot vers un fichier osm

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

    logger.info("Conversion from pivot to OSM format for a resource")

    used_bases = {}
    work_dir_config = config['workingSpace']['directory']

    # On vérifie le type de la ressource
    if (resource['type'] not in ['osrm', 'valhalla']):
        raise ValueError("Wrong resource type, should be in ['osrm','valhalla']")

    # Les outils de conversion utilisés par Valhalla ne lisent que du osm.pbf
    convert_osm_to_pbf = False
    if (resource['type'] == 'valhalla'):
        convert_osm_to_pbf = True

    # Comme chaque source de la ressource peut potentiellement nécessiter un pivot différent,
    # On fait une boucle sur les sources et on adapte en fonction du type
    for source in resource['sources']:

        logger.info("Create osm file of source: " + source['id'])

        # Les sources smartrouting n'ont pas besoin de génération mais peuvent apparaître dans certaines ressources
        if source['type'] == 'smartrouting':
            logger.info("Smartrouting source, no need for osm file")
            continue

        # Plusieurs sources peuvent référencer le même mapping mais changer plus tard dans la génération
        found_base = False
        found_id = ''
        for sid,sub in used_bases.items():
            if sub == source['mapping']['source']['baseId']:
                found_base = True
                found_id = sid

        if found_base:

            if convert_osm_to_pbf:
                linked_file = os.path.join(work_dir_config, source['id'] + ".osm.pbf")
                real_file = os.path.join(work_dir_config, found_id + ".osm.pbf")
            else:
                linked_file = os.path.join(work_dir_config, source['id'] + ".osm")
                real_file = os.path.join(work_dir_config, found_id + ".osm")

            logger.info("Mapping already done, creating a linked osm file : " + linked_file + " -> " + real_file)
            if not os.path.islink(linked_file):
                os.symlink(real_file, linked_file)
            else:
                ex_link = os.readlink(linked_file)
                ex_link = os.path.join(os.path.dirname(linked_file), ex_link)
                if ex_link != real_file:
                    raise ValueError("SymLink is already pointing to another file")
                else:
                    logger.info("SymLink already pointing to the good file")

        else:
            logger.info("Mapping not already done")
            pivot_to_osm(config, source, db_configs, connection, logger, convert_osm_to_pbf)

        used_bases[ source['id'] ] = source['mapping']['source']['baseId']

def osrm_convert(config, resource, logger, build_lua_from_cost_config = True):
    """
    Fonction de conversion depuis le fichier osm vers les fichiers osrm

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    logger: logging.Logger
    build_lua_from_cost_config : bool
        contruire le lua à partir de le configuration des coûts. Défaut : True
    """

    if (resource['type'] != 'osrm'):
        raise ValueError("Wrong resource type, should be 'osrm'")

    logger.info("Conversion from OSM to OSRM for a resource")

    logger.info("Generating graphs for each cost...")
    cpu_count = multiprocessing.cpu_count()
    work_dir_config = config['workingSpace']['directory']

    i = 0
    for source in resource["sources"]:

        logger.info("Source {} of {}...".format(i+1, len(resource["sources"])))

        logger.info('LUA part')
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

        logger.info('Recherche du fichier OSM')

        osm_file = os.path.join(work_dir_config, source['id'] + ".osm")
        extension = ".osm"
        if not os.path.exists(osm_file):
            osm_pbf_file = os.path.join(work_dir_config, source['id'] + ".osm.pbf")
            if not os.path.exists(osm_pbf_file):
                raise ValueError("Can't find osm file")
            else:
                osm_file = osm_pbf_file
                extension = ".osm.pbf"

        logger.info('Fichier OSM trouvé: ' + osm_file)

        # Gestion des points "." dans le chemin d'accès avec ".".join()
        osrm_file = source["storage"]["file"]
        cost_dir = os.path.dirname(osrm_file)
        profile_name = osrm_file.split("/")[-1].split(".")[0]
        tmp_osm_file = "{}/{}{}".format(cost_dir, profile_name, extension)

        # Définition des commandes shell à exécuter
        mkdir_args = ["mkdir", "-p", cost_dir]
        copy_args = ["cp", ".".join(osm_file.split(".")[:-1]) + extension, tmp_osm_file]
        osrm_extract_args = ["osrm-extract", tmp_osm_file, "-p", lua_file, "-t", cpu_count]
        osrm_contract_args = ["osrm-contract", osrm_file, "-t", cpu_count]
        rm_args = ["rm", tmp_osm_file]

        subprocess_execution(mkdir_args, logger)
        subprocess_execution(copy_args, logger)
        start_command = time.time()
        subprocess_execution(osrm_extract_args, logger)
        end_command = time.time()
        logger.info("OSRM extract ended. Elapsed time : %s seconds." %(end_command - start_command))
        subprocess_execution(osrm_contract_args, logger)
        final_command = time.time()
        logger.info("OSRM contract ended. Elapsed time : %s seconds." %(final_command - end_command))
        subprocess_execution(rm_args, logger)
        i += 1


def valhalla_convert(config, resource, logger, build_lua_from_cost_config = True):
    """
    Fonction de conversion depuis le fichier .osm.pbf vers les fichiers valhalla

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    resource: dict
        dictionnaire correspondant à la resource décrite dans le fichier passé en argument
    logger: logging.Logger
    build_lua_from_cost_config : bool
        contruire le lua à partir de le configuration des coûts. Défaut : True
    """

    if (resource['type'] != 'valhalla'):
        raise ValueError("Wrong resource type, should be 'valhalla'")

    logger.info("Conversion from OSM PBF to VALHALLA for a resource")

    logger.info("Generating graphs for each set of tiles")

    work_dir_config = config['workingSpace']['directory']

    i = 0
    for source in resource["sources"]:

        logger.info("Source {} of {}...".format(i+1, len(resource["sources"])))

        logger.info('Looking for OSM PBF file')

        osm_file = os.path.join(work_dir_config, source['id'] + ".osm.pbf")
        extension = ".osm.pbf"
        if not os.path.exists(osm_file):
            # On gère le cas où une génération a déjà été lancée pour du OSRM donc en .osm et pas forcément pbf
            osm_tmp_file = os.path.join(work_dir_config, source['id'] + ".osm")
            if not os.path.exists(osm_tmp_file):
                raise ValueError("Can't find osm file")
            else:
                logger.info("OSM file found, conversion to pbf")
                osm_to_pbf(osm_tmp_file, osm_file, logger)

        logger.info('OSM PBF file found: ' + osm_file)

        # Todo : modifier toute cette partie LUA
        # actuellement, on génère un seul LUA pour tous les coûts possibles (car/fastest, car/shortest, pedestrian/shortest)
        # Mais il serait bien de générer le LUA avec les coûts qui sont dans costs uniquement
        logger.info('LUA part')

        lua_file = source["costs"][0]["compute"]["storage"]["file"]

        if build_lua_from_cost_config:
            logger.info("Building lua profile")
            config_file = source["costs"][0]["compute"]["configuration"]["storage"]["file"]
            costs_config = config_from_path(config_file)

            with open(lua_file, "w") as lua_f:
                lua_f.write(build_valhalla_lua(costs_config))
            logger.info("Finished lua building")

        # Définition et exécution des commandes shell à exécuter
        mkdir_args = ["mkdir", "-p", source["storage"]["dir"]]
        subprocess_execution(mkdir_args, logger)

        start_command = time.time()
        valhalla_build_config_args = ["valhalla_build_config",
            "--mjolnir-tile-dir",  source["storage"]["dir"],
            "--mjolnir-tile-extract", source["storage"]["tar"]]
        subprocess_execution(valhalla_build_config_args, logger, outfile = source["storage"]["config"])
        # Nécessaire le temps que le fichier s'écrive...
        time.sleep(1)
        # Ajout du graph custom dans la config valhalla
        with open(source["storage"]["config"], "r") as valhalla_config:
            config_dict = json.load(valhalla_config)
            config_dict["mjolnir"]["graph_lua_name"] = source["costs"][0]["compute"]["storage"]["file"]
            # Ajout de l'autorisation à exclure les ponts/tunnels/péages
            config_dict["service_limits"]["allow_hard_exclusions"] = True

        with open(source["storage"]["config"], "w") as valhalla_config:
            valhalla_config.write(json.dumps(config_dict))

        valhalla_build_tiles_args = ["valhalla_build_tiles", "-c", source["storage"]["config"], osm_file]
        subprocess_execution(valhalla_build_tiles_args, logger)

        valhalla_build_extract_args = ["valhalla_build_extract", "-c", source["storage"]["config"], "-v"]
        subprocess_execution(valhalla_build_extract_args, logger)

        final_command = time.time()
        logger.info("Valhalla tiles built. Elapsed time : %s seconds." %(final_command - start_command))


def write_road2_config(config, resource, logger, convert_file_paths = True):
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

    logger.info("Writing sources")

    os.makedirs(config["outputs"]["configurations"]["sources"]["storage"]["directory"] or '.', exist_ok=True)

    source_ids = []

    for source in resource["sources"]:

        source_file = os.path.join(config["outputs"]["configurations"]["sources"]["storage"]["directory"], source['id'] + ".source")
        logger.info("Writing source file : " + source_file)

        # On modifie la source en fonction de son type
        if source['type'] == 'smartrouting':
            logger.info("Smartrouting source, no need for modifications")
        elif source['type'] == 'osrm':
            source.pop("mapping", None)
            source["cost"].pop("compute", None)
        elif source['type'] == "valhalla":
            source.pop("mapping", None)
            for cost in source["costs"]:
                cost.pop("compute", None)
        elif source['type'] == "pgr":
            source.pop("mapping", None)
            bid_tmp = source["storage"]["base"]["baseId"]
            for base in config["bases"]:
                if base["id"] == bid_tmp:
                    db_file_out = convert_path(base["configFile"], config["outputs"]["configurations"]["databases"]["storage"]["directory"])
                    copy_file_locally(base["configFile"], db_file_out)
                    source["storage"]["base"].update({"dbConfig":db_file_out})
                    source["storage"]["base"].update({"schema":base["schema"]})
            source["storage"]["base"].pop("baseId", None)
            for cost in source["costs"]:
                cost.pop("compute", None)
        else:
            continue

        # Écriture du fichier
        with open(source_file, "w") as source_file:
            json_string = json.dumps(source, indent=2)
            source_file.write(json_string)

        source_ids.append(source['id'])

    # On passe à la ressource
    resource_file = os.path.join(config["outputs"]["configurations"]["resource"]["storage"]["directory"], resource['id'] + ".resource")
    logger.info("Writing resource file: " + resource_file)

    # Récupération de la date d'extraction
    work_dir_config = config['workingSpace']['directory']
    date_file = os.path.join(work_dir_config, "r2gg.date")
    f = open(date_file, "r")
    extraction_date = f.read()
    logger.info("extraction date to add in resource (from "+ date_file +"): " + extraction_date)
    f.close()

    # On fait le dossier s'il n'existe pas
    os.makedirs(config["outputs"]["configurations"]["resource"]["storage"]["directory"] or '.', exist_ok=True)
    # On modifie l'objet resource
    resource['sources'] = source_ids
    resource["resourceVersion"] = extraction_date

    final_resource = {"resource": resource}
    with open(resource_file, "w") as resource_file:
        json_string = json.dumps(final_resource, indent=2)
        resource_file.write(json_string)
