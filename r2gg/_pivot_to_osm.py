from math import ceil
import os
import time

from lxml import etree
from psycopg2.extras import DictCursor

from r2gg._osm_building import writeNode, writeWay, writeWayNds, writeRes, writeWayTags
from r2gg._sql_building import getQueryByTableAndBoundingBox

def pivot_to_osm(resource, connection, logger):
    """
    Fonction de conversion depuis la bdd pivot vers le fichier osm

    Parameters
    ----------
    resource: dict
    connection: psycopg2.connection
        connection à la bdd de travail
    logger: logging.Logger
    """

    cursor = connection.cursor(cursor_factory=DictCursor)

    logger.info("SQL: select last_value from nodes_id_seq")
    cursor.execute("select last_value from nodes_id_seq")
    vertexSequence = cursor.fetchone()[0]
    logger.info(vertexSequence)

    logger.info("SQL: select last_value from edges_id_seq")
    cursor.execute("select last_value from edges_id_seq")
    edgeSequence = cursor.fetchone()[0]
    logger.info(edgeSequence)

    logger.info("Starting conversion from pivot to OSM")
    start_time = time.time()

    filename = resource['topology']['storage']['file']
    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)

    with etree.xmlfile(filename, encoding='utf-8', close=True) as xf:
        xf.write_declaration()
        attribs = {"version": "0.6", "generator": "r2gg 0.0.1"}
        with xf.element("osm", attribs):

            # Ecriture des nodes
            sql_query = getQueryByTableAndBoundingBox('nodes', resource['topology']['bbox'])
            logger.info("SQL: {}".format(sql_query))
            st_execute = time.time()
            cursor.execute(sql_query)
            et_execute = time.time()
            logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
            row = cursor.fetchone()
            logger.info("Writing nodes")
            st_execute = time.time()
            i = 1
            while row:
                nodeEl = writeNode(row)
                xf.write(nodeEl, pretty_print=True)
                row = cursor.fetchone()
                if (i % ceil(cursor.rowcount/10) == 0):
                    logger.info("%s / %s nodes ajoutés" %(i, cursor.rowcount))
                i += 1
            et_execute = time.time()
            logger.info("Writing nodes ended. Elapsed time : %s seconds." %(et_execute - st_execute))

            # Ecriture des ways
            sql_query2 = getQueryByTableAndBoundingBox('edges', resource['topology']['bbox'], ['*', 'inter_nodes(geom) as internodes'])
            logger.info("SQL: {}".format(sql_query2))
            st_execute = time.time()
            cursor.execute(sql_query2)
            et_execute = time.time()
            logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
            row = cursor.fetchone()
            logger.info("Writing ways")
            st_execute = time.time()
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
                row = cursor.fetchone()
                if (i % ceil(cursor.rowcount/10) == 0):
                    logger.info("%s / %s ways ajoutés" %(i, cursor.rowcount))
                i += 1
            et_execute = time.time()
            logger.info("Writing ways ended. Elapsed time : %s seconds." %(et_execute - st_execute))

            # Ecriture des restrictions
            sql_query3 = "select * from non_comm"
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
                ResEl = writeRes(row,i)
                xf.write(ResEl, pretty_print=True)
                row = cursor.fetchone()
                if (i % ceil(cursor.rowcount/10) == 0):
                    logger.info("%s / %s restrictions ajoutés" %(i, cursor.rowcount))
                i += 1
            et_execute = time.time()
            logger.info("Writing restrictions ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    cursor.close()
    end_time = time.time()
    logger.info("Conversion from pivot to OSM ended. Elapsed time : %s seconds." %(end_time - start_time))
