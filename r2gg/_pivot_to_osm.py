import time

from lxml import etree
from psycopg2.extras import DictCursor

from _osm_building import writeNode, writeWay, writeWayNds, writeRes, writeWayTags
from _sql_building import getQueryByTableAndBoundingBox

def pivot_to_osm(resource, connection, logger):
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
            sql_query = getQueryByTableAndBoundingBox('nodes', resource['boundingBox'])
            logger.info("SQL: {}".format(sql_query))
            cursor.execute(sql_query)
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
            sql_query2 = getQueryByTableAndBoundingBox('edges', resource['boundingBox'], ['*', 'inter_nodes(geom) as internodes'])
            logger.info("SQL: {}".format(sql_query2))
            cursor2.execute(sql_query2)
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
            sql_query3 = "select * from bduni_non_com"
            logger.info("SQL: {}".format(sql_query3))
            cursor.execute(sql_query3)
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
    end_time = time.time()
    logger.info("Conversion ended. Elapsed time : %s seconds." %(end_time - start_time))
