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

    logger.info("Starting conversion")
    start_time = time.time()

    filename = resource['topology']['storage']['file']
    os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)

    with open(filename, "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration()
        attribs = {"version": "0.6", "generator": "r2gg 0.0.1"}
        with xf.element("osm", attribs):

            # Ecriture des nodes
            sql_query = getQueryByTableAndBoundingBox('nodes', resource['boundingBox'])
            logger.info("SQL: {}".format(sql_query))
            cursor.execute(sql_query)
            row = cursor.fetchone()
            i = 1
            while row:
                nodeEl = writeNode(row)
                xf.write(nodeEl, pretty_print=True)
                row = cursor.fetchone()
                if (i % int(cursor.rowcount/10) == 0):
                    logger.info("%s / %s nodes ajoutés" %(i, cursor.rowcount))
                i += 1

            # Ecriture des ways
            sql_query2 = getQueryByTableAndBoundingBox('edges', resource['boundingBox'], ['*', 'inter_nodes(geom) as internodes'])
            logger.info("SQL: {}".format(sql_query2))
            cursor.execute(sql_query2)
            row = cursor.fetchone()
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
                if (i % int(cursor.rowcount/10) == 0):
                    logger.info("%s / %s ways ajoutés" %(i, cursor.rowcount))
                i += 1

            # Ecriture des restrictions
            sql_query3 = "select * from non_comm"
            logger.info("SQL: {}".format(sql_query3))
            cursor.execute(sql_query3)
            row = cursor.fetchone()
            i = 1
            while row:
                if row['common_vertex_id'] == -1:
                    row = cursor.fetchone()
                    i += 1
                    continue
                ResEl = writeRes(row,i)
                xf.write(ResEl, pretty_print=True)
                row = cursor.fetchone()
                if (i % int(cursor.rowcount/10) == 0):
                    logger.info("%s / %s restrictions ajoutés" %(i, cursor.rowcount))
                i += 1

    cursor.close()
    end_time = time.time()
    logger.info("Conversion ended. Elapsed time : %s seconds." %(end_time - start_time))
