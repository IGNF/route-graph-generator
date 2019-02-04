# coding: utf8

import time
import argparse
import logging
import subprocess

from lxml import etree
import psycopg2
from psycopg2.extras import DictCursor, LoggingConnection
# https://github.com/andialbrecht/sqlparse
import sqlparse

from _read_config import config_from_path
from _osm_building import writeNode, writeWay, writeWayNds, writeRes, writeWayTags
from _sql_building import getQueryByTableAndBoundingBox

def _configure():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file_path', type=str)
    config_path = parser.parse_args().config_file_path

    return config_path

def execute():
    # Lecture configuration
    config_path = _configure()
    # Récupération de l'objet 'génération' qui contient toute la config
    config = config_from_path(config_path)['generation']

    # Récupération de la configuration du log
    logs_config = config_from_path( config['general']['logs']['configFile'] )

    # Gestion du fichiers de logs non spécifié
    try:
        logs_file = logs_config['filename']
    except KeyError:
        logs_file = '/dev/null'

    # Définition des niveaux de log
    levels = {
        'CRITICAL' : logging.CRITICAL,
        'ERROR' : logging.ERROR,
        'WARNING' : logging.WARNING,
        'INFO' : logging.INFO,
        'DEBUG' : logging.DEBUG
    }

    # Configuration du module logging
    a = logging.FileHandler(logs_file)
    logging.basicConfig(
        format='%(asctime)s %(message)s',
        level=levels[ logs_config['level'].upper() ],
        handlers=[
            a,
            logging.StreamHandler()
        ])

    # Initialisation du logger
    logger = logging.getLogger(__name__)

    # Configuration des bases de données précisées dans la config
    db_configs = { base['id']: config_from_path(base['configFile']) for base in config['bases'] if base['type'] == 'bdd' }

    # Configuration de la bdd source
    source_config = db_configs[ config['resource']['topology']['mapping']['source']['baseId'] ]

    # Configuration de la bdd de travail
    work_db_config = db_configs[ config['workingSpace']['baseId'] ]

    # Récupération des paramètres de la bdd
    host = work_db_config.get('host')
    dbname = work_db_config.get('dbname')
    user = work_db_config.get('username')
    password = work_db_config.get('password')
    port = work_db_config.get('port')
    connect_args = 'host=%s dbname=%s user=%s password=%s' %(host, dbname, user, password)

    # Récupération de l'objet permettant de générer la ressource
    resource = config['resource']

    logger.info("Connecting to work database")
    connection = psycopg2.connect(connect_args)
    connection.set_client_encoding('UTF8')

    # subprocess.check_output("""PGPASSWORD={} PGUSER={} PGHOST={} PGPORT={} psql -d {} -v cuser={} -v bdpwd={} -v bdport={} -v bdhost={} -v bduser={} -v bdname={} -f {}
    #     """.format(password, user, host, port, dbname,
    #         user, source_config.get('password'), source_config.get('port'), source_config.get('host'), source_config.get('username'), source_config.get('dbname'),
    #         resource['topology']['mapping']['storage']['file']
    #     )
    # )
    with open( resource['topology']['mapping']['storage']['file'] ) as sql_script:
        cur = connection.cursor()
        logger.info("Executing SQL conversion script")
        instructions = sqlparse.split(sql_script.read().format(user=user))

        for instruction in instructions:
            if instruction == '':
                continue
            logger.debug("SQL:\n {}\n".format(instruction) )
            cur.execute(instruction,
                {'bdpwd': source_config.get('password'), 'bdport': source_config.get('port'),
                'bdhost': source_config.get('host'), 'bduser': source_config.get('username'), 'dbname': source_config.get('dbname')
            })
        connection.commit()

    cursor = connection.cursor(cursor_factory=DictCursor)
    cursor2 = connection.cursor(cursor_factory=DictCursor, name='server_cursor') # Server side cursor

    logger.info("SQL: select last_value from bduni_vertex_id_seq")
    cursor.execute("select last_value from bduni_vertex_id_seq")
    vertexSequence = cursor.fetchone()[0]
    logger.info(vertexSequence)

    logger.info("SQL: select last_value from bduni_edge_id_seq")
    cursor.execute("select last_value from bduni_edge_id_seq")
    edgeSequence = cursor.fetchone()[0]
    logger.info(edgeSequence)

    logger.info("Starting conversion")
    start_time = time.time()

    with open(resource['topology']['storage']['file'], "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration()
        attribs = {"version": "0.6", "generator": "r2gg 0.0.1"}
        with xf.element("osm", attribs):

            # Ecriture des nodes
            logger.info("SQL: {}".format(getQueryByTableAndBoundingBox('bduni_vertex', config['resource']['boundingBox'])))
            cursor.execute(getQueryByTableAndBoundingBox('bduni_vertex', config['resource']['boundingBox']))
            row = cursor.fetchone()
            i = 1
            while row:
                nodeEl = writeNode(row)
                xf.write(nodeEl, pretty_print=True)
                row = cursor.fetchone()
                if (i % int(vertexSequence/10) == 0):
                    logger.info("%s / %s nodes ajoutés" %(i, vertexSequence))
                i += 1

            # Ecriture des ways
            logger.info("SQL: {}".format(getQueryByTableAndBoundingBox('bduni_edge',
                config['resource']['boundingBox'], ['*', 'inter_nodes(geom) as internodes']))
            )
            cursor2.execute(getQueryByTableAndBoundingBox('bduni_edge', config['resource']['boundingBox'], ['*', 'inter_nodes(geom) as internodes']))
            row = cursor2.fetchone()
            i = 1
            while row:
                wayEl = writeWay(row)
                for node in row['internodes']:
                    vertexSequence = vertexSequence + 1
                    node['id'] = vertexSequence
                    nodeEl = writeNode(node)
                    xf.write(nodeEl, pretty_print=True)
                wayEl = writeWayNds(wayEl, row, row['internodes'])
                wayEl = writeWayTags(wayEl, row)
                xf.write(wayEl, pretty_print=True)
                row = cursor2.fetchone()
                if (i % int(edgeSequence/10) == 0):
                    logger.info("%s / %s ways ajoutés" %(i, edgeSequence))
                i += 1

            # Ecriture des restrictions
            cursor.execute("select * from bduni_non_com")
            i = 1
            for row in cursor:
                if row['common_vertex_id']==0:
                    i += 1
                    continue
                ResEl = writeRes(row,i)
                xf.write(ResEl, pretty_print=True)
                if (i % 1000 == 0):
                    logger.info("%s / %s restrictions ajoutés" %(i, cursor.rowcount))
                i += 1
    cursor.close()
    cursor2.close()
    connection.close()
    end_time = time.time()
    logger.info("Conversion ended. Elapsed time : %s seconds." %(end_time - start_time))
