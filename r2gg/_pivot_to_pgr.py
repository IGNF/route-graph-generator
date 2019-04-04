import math
import time

from psycopg2.extras import DictCursor

from r2gg._output_costs_from_costs_config import output_costs_from_costs_config
from r2gg._read_config import config_from_path
from r2gg._sql_building import getQueryByTableAndBoundingBox

def pivot_to_pgr(resource, connection_work, connection_out, logger, turn_restrictions=True):
    cursor_in = connection_work.cursor(cursor_factory=DictCursor)

    # Récupération des coûts à calculer
    costs = config_from_path(resource["costs"]["compute"]["storage"]["file"])

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
            rule text,
            one_way int ,
            oneway TEXT ,
            x1 double precision,
            y1 double precision,
            x2 double precision,
            y2 double precision,
            maxspeed_forward double precision,
            maxspeed_backward double precision,
            priority double precision DEFAULT 1,
            the_geom geometry(Linestring,4326)
        );"""
    logger.debug("SQL: {}".format(create_table))
    cursor_out.execute(create_table)

    # Ajout des colonnes de coûts
    add_columns = "ALTER TABLE ways "
    for output in costs["outputs"]:
        add_columns += "ADD COLUMN IF NOT EXISTS {} double precision,".format(output["name"])
        add_columns += "ADD COLUMN IF NOT EXISTS {} double precision,".format("reverse_" + output["name"])
    add_columns = add_columns[:-1]
    logger.debug("SQL: adding costs columns \n {}".format(add_columns))
    cursor_out.execute(add_columns)

    if turn_restrictions:
        logger.info("Writing turn restrinctions...")
        create_non_comm = """
            DROP TABLE IF EXISTS turn_restrictions;
            CREATE TABLE turn_restrictions(
                id text unique,
                id_from bigint,
                id_to bigint
        );"""
        logger.debug("SQL: {}".format(create_non_comm))
        cursor_out.execute(create_non_comm)
        
        logger.info("Populating turn restrictions")
        tr_query = "SELECT id_from, id_to FROM non_comm;"

        logger.debug("SQL: {}".format(tr_query))
        cursor_in.execute(tr_query)
        rows = cursor_in.fetchall()
        # Insertion petit à petit -> plus performant
        logger.info("SQL: Inserting or updating {} values in out db".format(len(rows)))
        index = 0
        for i in range(math.ceil(len(rows)/1000)):
            tmp_rows = rows[i*1000:(i+1)*1000]
            values_str = ""
            for row in tmp_rows:
                values_str += "(%s, %s, %s),"
            values_str = values_str[:-1]
            
            # Tuple des valuers à insérer
            values_tuple = ()
            for row in tmp_rows:
                values_tuple += (index, row['id_from'], row['id_to'])
                index += 1

            sql_insert = """
                INSERT INTO turn_restrictions (id, id_from, id_to)
                VALUES {}
            """.format(values_str)
            cursor_out.execute(sql_insert, values_tuple)
            connection_out.commit()
        
        logger.info("Writing turn restrinctions Done")

    logger.info("Starting conversion")
    start_time = time.time()

    # Colonnes à lire dans la base source (champs classiques + champs servant aux coûts)
    in_columns = [
            'id',
            'geom',
            'ST_Length(geom) as length',
            'length_m as length_m'
        ]
    for variable in costs["variables"]:
        in_columns += [variable["column_name"]]

    # Ecriture des ways
    sql_query = getQueryByTableAndBoundingBox('edges', resource['boundingBox'], in_columns)
    logger.info("SQL: {}".format(sql_query))
    cursor_in.execute(sql_query)
    rows = cursor_in.fetchall()

    # Chaîne de n %s, pour l'insertion de données via psycopg
    single_value_str = "%s," * (4 + 2 * len(costs["outputs"]))
    single_value_str = single_value_str[:-1]

    # Insertion petit à petit -> plus performant
    logger.info("SQL: Inserting or updating {} values in out db".format(len(rows)))
    for i in range(math.ceil(len(rows)/1000)):
        tmp_rows = rows[i*1000:(i+1)*1000]
        # Chaîne permettant l'insertion de valeurs via psycopg
        values_str = ""
        for row in tmp_rows:
            values_str += "(" + single_value_str + "),"
        values_str = values_str[:-1]

        # Tuple des valuers à insérer
        values_tuple = ()
        for row in tmp_rows:
            output_costs = output_costs_from_costs_config(costs, row)
            values_tuple += (row['id'], row['geom'], row['length'], row['length_m']) + output_costs

        output_columns = "(id, the_geom, length, length_m"
        set_on_conflict = "the_geom = excluded.the_geom,length = excluded.length,length_m = excluded.length_m"
        for output in costs["outputs"]:
            output_columns += ", " + output["name"] + ", reverse_" + output["name"]
            set_on_conflict += ",{0} = excluded.{0}".format(output["name"])
            set_on_conflict += ",{0} = excluded.{0}".format("reverse_" + output["name"])

        output_columns += ")"
        sql_insert = """
            INSERT INTO ways {}
            VALUES {}
            ON CONFLICT (id) DO UPDATE
              SET {};
            """.format(output_columns, values_str, set_on_conflict)
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
