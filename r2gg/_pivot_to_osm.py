from datetime import date
from math import ceil
import os
import time

from lxml import etree
from psycopg2.extras import DictCursor

from r2gg._osm_building import writeNode, writeWay, writeWayNds, writeRes, writeWayTags
from r2gg._sql_building import getQueryByTableAndBoundingBox
from r2gg._osm_to_pbf import osm_to_pbf


def pivot_to_osm(config, source, db_configs, connection, logger, output_is_pbf = False):
    """
    Fonction de conversion depuis la bdd pivot vers le fichier osm puis pbf le cas échéant

    Parameters
    ----------
    config: dict
        dictionnaire correspondant à la configuration décrite dans le fichier passé en argument
    source: dict
    db_configs: dict
        dictionnaire correspondant aux configurations des bdd
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """

    logger.info("Convert pivot to OSM format for a source")

    # Récupération de la date d'extraction
    work_dir_config = config['workingSpace']['directory']

    # Get extraction date from file or use current date
    date_file = os.path.join(work_dir_config, "r2gg.date")
    if os.path.exists(date_file):
        f = open(date_file, "r")
        extraction_date = f.read()
        f.close()
    else:
        extraction_date = date.today().strftime("%Y-%m-%d")

    source_db_config = db_configs[source['mapping']['source']['baseId']]
    input_schema = source_db_config.get('schema')

    cursor = connection.cursor(cursor_factory=DictCursor)

    logger.info(f"SQL: select last_value from {input_schema}.nodes_id_seq")
    cursor.execute(f"select last_value from {input_schema}.nodes_id_seq")
    vertexSequence = cursor.fetchone()[0]
    logger.info(vertexSequence)

    logger.info(f"SQL: select last_value from {input_schema}.edges_id_seq")
    cursor.execute(f"select last_value from {input_schema}.edges_id_seq")
    edgeSequence = cursor.fetchone()[0]
    logger.info(edgeSequence)

    logger.info("Starting conversion from pivot to OSM")
    start_time = time.time()

    filename = os.path.join(work_dir_config, source['id'] + ".osm")
    logger.info("OSM file to write : " + filename)

    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
    try:
        with etree.xmlfile(filename, encoding='utf-8', close=True) as xf:
            xf.write_declaration()
            attribs = {"version": "0.6", "generator": "r2gg"}
            with xf.element("osm", attribs):

                # Récupération du nombre de nodes
                sql_query = f"SELECT COUNT(*) as cnt FROM {input_schema}.nodes"
                logger.info("SQL: {}".format(sql_query))
                st_execute = time.time()
                cursor.execute(sql_query)
                et_execute = time.time()
                logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
                row = cursor.fetchone()
                nodesize = row["cnt"]

                # Ecriture des nodes
                batchsize = 500000
                offset = 0
                logger.info(f"Writing nodes: {nodesize} ways to write")
                st_nodes = time.time()
                while offset < nodesize:
                  sql_query = getQueryByTableAndBoundingBox(f'{input_schema}.nodes', source['bbox'])
                  sql_query += " LIMIT {} OFFSET {}".format(batchsize, offset)
                  logger.info("SQL: {}".format(sql_query))
                  st_execute = time.time()
                  cursor.execute(sql_query)
                  et_execute = time.time()
                  offset += batchsize
                  logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
                  row = cursor.fetchone()
                  logger.info("Writing nodes")
                  st_execute = time.time()
                  i = 1
                  while row:
                      nodeEl = writeNode(row, extraction_date)
                      xf.write(nodeEl, pretty_print=True)
                      row = cursor.fetchone()
                  logger.info("%s / %s nodes ajoutés" %(offset, nodesize))
                et_nodes = time.time()
                logger.info("Writing nodes ended. Elapsed time : %s seconds." %(et_nodes - st_nodes))

                # Récupération du nombre de ways
                sql_query = f"SELECT COUNT(*) as cnt FROM {input_schema}.edges"
                logger.info("SQL: {}".format(sql_query))
                st_execute = time.time()
                cursor.execute(sql_query)
                et_execute = time.time()
                logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
                row = cursor.fetchone()
                edgesize = row["cnt"]

                # Ecriture des ways
                batchsize = 300000
                offset = 0
                logger.info(f"Writing ways: {edgesize} ways to write")
                st_edges = time.time()
                while offset < edgesize:
                  sql_query2 = getQueryByTableAndBoundingBox(f'{input_schema}.edges', source['bbox'], ['*', f'{input_schema}.inter_nodes(geom) as internodes'])
                  sql_query2 += " LIMIT {} OFFSET {}".format(batchsize, offset)
                  logger.info("SQL: {}".format(sql_query2))
                  st_execute = time.time()
                  cursor.execute(sql_query2)
                  et_execute = time.time()
                  offset += batchsize
                  logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
                  row = cursor.fetchone()
                  st_execute = time.time()
                  i = 1
                  while row:
                      wayEl = writeWay(row, extraction_date)
                      for node in row['internodes']:
                          vertexSequence = vertexSequence + 1
                          node['id'] = vertexSequence
                          nodeEl = writeNode(node, extraction_date)
                          xf.write(nodeEl, pretty_print=True)
                      wayEl = writeWayNds(wayEl, row, row['internodes'])
                      wayEl = writeWayTags(wayEl, row)
                      xf.write(wayEl, pretty_print=True)
                      row = cursor.fetchone()
                  logger.info("%s / %s ways ajoutés" %(offset, edgesize))
                et_edges = time.time()
                logger.info("Writing ways ended. Elapsed time : %s seconds." %(et_edges - st_edges))

                # Ecriture des restrictions
                sql_query3 = f"select * from {input_schema}.non_comm"
                logger.info("SQL: {}".format(sql_query3))
                st_execute = time.time()
                cursor.execute(sql_query3)
                et_execute = time.time()
                logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
                row = cursor.fetchone()
                logger.info("Writing restrictions")
                st_execute = time.time()
                i = 1
                while row:
                    if row['common_vertex_id'] == -1:
                        row = cursor.fetchone()
                        i += 1
                        continue
                    ResEl = writeRes(row, i, extraction_date)
                    xf.write(ResEl, pretty_print=True)
                    row = cursor.fetchone()
                    if (i % ceil(cursor.rowcount/10) == 0):
                        logger.info("%s / %s restrictions ajoutés" %(i, cursor.rowcount))
                    i += 1
                et_execute = time.time()
                logger.info("Writing restrictions ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    except etree.SerialisationError:
        logger.warn("WARNING: XML file not closed properly (lxml.etree.SerialisationError)")

    cursor.close()
    end_time = time.time()
    logger.info("Conversion from pivot to OSM ended. Elapsed time : %s seconds." %(end_time - start_time))

    # osm2pbf : Gestion du format osm.pbf
    if output_is_pbf:
        osm_to_pbf(filename, filename+'.pbf', logger)
