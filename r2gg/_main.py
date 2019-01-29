# coding: utf8

import psycopg2
import psycopg2.extras
import time
import argparse
import logging

from lxml import etree

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
    logging.basicConfig(
        format='%(asctime)s %(message)s',
        level=levels[ logs_config['level'].upper() ],
        handlers=[
            logging.FileHandler(logs_file),
            logging.StreamHandler()
        ])

    # Initialisation du logger
    logger = logging.getLogger(__name__)

    # Configuration des bases de données précisées dans la config
    db_configs = { base['id']: config_from_path(base['configFile']) for base in config['bases'] if base['type'] == 'bdd' }

    # Configuration de la bdd source
    source_config = db_configs[ config['resource']['topology']['mapping']['source']['baseId'] ]

    # Récupération des paramètres de la bdd
    host = source_config.get('host')
    dbname = source_config.get('dbname')
    user = source_config.get('username')
    password = source_config.get('password')
    connect_args = 'host=%s dbname=%s user=%s password=%s' %(host, dbname, user, password)

    # Récupération de l'objet permettant de générer la ressource
    resource = config['resource']

    logger.info("Connecting to source database")
    connection = psycopg2.connect(connect_args)
    connection.set_client_encoding('UTF8')
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor2 = connection.cursor(cursor_factory=psycopg2.extras.DictCursor, name='server_cursor') # Server side cursor

    logger.info("SQL: select last_value from bduni_vertex_id_seq")
    cursor.execute("select last_value from bduni_vertex_id_seq")
    vertexSequence = cursor.fetchone()[0]
    logger.info("SQL: select last_value from bduni_edge_id_seq")
    cursor.execute("select last_value from bduni_edge_id_seq")
    edgeSequence = cursor.fetchone()[0]

    logger.info("Starting conversion")
    start_time = time.time()

    with open(resource['topology']['storage']['file'], "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration()
        attribs = {"version": "0.6", "generator": "r2gg 0.0.1"}
        with xf.element("osm", attribs):

            # Ecriture des nodes
            cursor.execute(getQueryByTableAndBoundingBox('bduni_vertex', config['resource']['boundingBox'] ))
            row = cursor.fetchone()
            i = 1
            while row:
                nodeEl = writeNode(row)
                xf.write(nodeEl, pretty_print=True)
                row = cursor.fetchone()
                if i % 100000 == 0:
                    logger.info("%s / %s nodes ajoutés" %(i, vertexSequence))
                i += 1

            # Ecriture des ways
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
                if (i % 100000 == 0):
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
