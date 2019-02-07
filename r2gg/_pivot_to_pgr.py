import time

from psycopg2.extras import DictCursor
from _sql_building import getQueryByTableAndBoundingBox

def pivot_to_pgr(resource, connection_work, connection_out, logger):

    cursor_in = connection_work.cursor(cursor_factory=DictCursor)

    cursor_out = connection_out.cursor()
    # Création de la edge_table pgrouting
    create_table = """
        CREATE TABLE IF NOT EXISTS ways(
            id bigserial unique,
            tag_id integer,
            length double precision,
            length_m double precision,
            name text,
            source bigint,
            target bigint,
            cost double precision,
            reverse_cost double precision,
            cost_s double precision ,
            reverse_cost_s double precision,
            rule text,
            one_way int ,
            oneway TEXT ,
            x1 double precision,
            y1 double precision,
            x2 double precision,
            y2 double precision,
            maxspeed_forward double precision,
            maxspeed_backward double precision,
            priority double precision DEFAULT 1
        );"""
    logger.debug("SQL: {}".format(create_table))
    cursor_out.execute(create_table)

    add_column = "ALTER TABLE ways ADD COLUMN IF NOT EXISTS the_geom geometry(Linestring,4326);"
    logger.debug("SQL: {}".format(add_column))
    cursor_out.execute(add_column)

    logger.info("SQL: select last_value from bduni_edge_id_seq")
    cursor_in.execute("select last_value from bduni_edge_id_seq")
    edgeSequence = cursor_in.fetchone()[0]
    logger.info(edgeSequence)

    logger.info("Starting conversion")
    start_time = time.time()

    # Ecriture des ways
    sql_query = getQueryByTableAndBoundingBox('bduni_edge', resource['boundingBox'], ['id', 'geom', 'ST_Length(geom) as length'])
    logger.info("SQL: {}".format(sql_query))
    cursor_in.execute(sql_query)
    rows = cursor_in.fetchall()

    values_str = ""
    for row in rows:
        values_str += "(%s, %s, %s, %s),"

    values_tuple = ()
    for row in rows:
        values_tuple += (row['id'], row['geom'], row['length'], row['length'])

    sql_insert = """
        INSERT INTO ways (id, the_geom, length, cost)
        VALUES {}
        ON CONFLICT (id) DO UPDATE
          SET the_geom = excluded.the_geom,
            length = excluded.length,
            cost = excluded.cost;
        """.format(values_str[:-1])
    logger.debug("SQL: Inserting {} values in out db".format(len(rows)))
    cursor_out.execute(sql_insert, values_tuple)
    connection_out.commit()

    # Ecriture des nodes et création de la topologie
    create_topology_sql = "SELECT pgr_createTopology('ways', 0.00001);"
    logger.info("SQL: {}".format(create_topology_sql))
    cursor_out.execute(create_topology_sql)
    connection_out.commit()


    # Check the routing topology
    analysegraph_sql = "SELECT pgr_analyzegraph('ways', 0.00001);"
    logger.info("SQL: {}".format(analysegraph_sql))
    cursor_out.execute(analysegraph_sql)
    connection_out.commit()


    # analyzeOneway_sql = "SELECT pgr_analyzeoneway('ways', 0.00001)"
    # logger.info("SQL: {}".format(analyzeOneway_sql))
    # cursor.execute(create_topology_sql)

    cursor_in.close()
    cursor_out.close()
    end_time = time.time()
    logger.info("Conversion ended. Elapsed time : %s seconds." %(end_time - start_time))
