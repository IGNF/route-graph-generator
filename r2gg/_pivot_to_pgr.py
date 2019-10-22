import math
import time

from psycopg2.extras import DictCursor

from r2gg._output_costs_from_costs_config import output_costs_from_costs_config
from r2gg._read_config import config_from_path
from r2gg._sql_building import getQueryByTableAndBoundingBox

def pivot_to_pgr(resource, cost_calculation_file_path, connection_work, connection_out, logger):
    """
    Fonction de conversion depuis la bdd pivot vers la base pgr

    Parameters
    ----------
    resource: dict
    cost_calculation_file_path: str
        chemin vers le fichier json de configuration des coûts
    connection_work: psycopg2.connection
        connection à la bdd de travail
    connection_out: psycopg2.connection
        connection à la bdd pgrouting de sortie
    logger: logging.Logger
    """

    cursor_in = connection_work.cursor(cursor_factory=DictCursor)

    # Récupération des coûts à calculer
    costs = config_from_path(cost_calculation_file_path)

    cursor_out = connection_out.cursor()
    # Création de la edge_table pgrouting
    create_table = """
        DROP TABLE IF EXISTS ways;
        CREATE TABLE ways(
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
            priority double precision DEFAULT 6,
            the_geom geometry(Linestring,4326),
            way_names text,
            nature text,
            vitesse_moyenne_vl integer,
            position_par_rapport_au_sol text,
            acces_vehicule_leger text
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

    logger.info("Starting conversion")
    start_time = time.time()

    # Non communications ---------------------------------------------------------------------------
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
    tr_query = "SELECT cleabs, id_from, id_to FROM non_comm;"

    logger.debug("SQL: {}".format(tr_query))
    st_execute = time.time()
    cursor_in.execute(tr_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    rows = cursor_in.fetchall()
    # Insertion petit à petit -> plus performant
    logger.info("SQL: Inserting or updating {} values in out db".format(len(rows)))
    st_execute = time.time()
    index = 0
    for i in range(math.ceil(len(rows)/10000)):
        tmp_rows = rows[i*10000:(i+1)*10000]
        values_str = ""
        for row in tmp_rows:
            values_str += "(%s, %s, %s),"
        values_str = values_str[:-1]

        # Tuple des valuers à insérer
        values_tuple = ()
        for row in tmp_rows:
            values_tuple += (row['cleabs'], row['id_from'], row['id_to'])
            index += 1

        set_on_conflict = (
            "id_from = excluded.id_from,id_to = excluded.id_to"
        )

        sql_insert = """
            INSERT INTO turn_restrictions (id, id_from, id_to)
            VALUES {}
            ON CONFLICT (id) DO UPDATE
              SET {};
        """.format(values_str, set_on_conflict)
        cursor_out.execute(sql_insert, values_tuple)
        connection_out.commit()

    et_execute = time.time()
    logger.info("Writing turn restrinctions Done. Elapsed time : %s seconds." %(et_execute - st_execute))

    # Noeuds ---------------------------------------------------------------------------------------
    logger.info("Writing vertices...")
    create_nodes = """
        DROP TABLE IF EXISTS ways_vertices_pgr;
        CREATE TABLE ways_vertices_pgr(
            id bigserial unique,
            cnt int,
            chk int,
            ein int,
            eout int,
            the_geom geometry(Point,4326)
    );"""
    logger.debug("SQL: {}".format(create_nodes))
    cursor_out.execute(create_nodes)

    logger.info("Populating vertices")
    nd_query = "SELECT id, geom FROM nodes;"

    logger.debug("SQL: {}".format(nd_query))
    st_execute = time.time()
    cursor_in.execute(nd_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    rows = cursor_in.fetchall()
    # Insertion petit à petit -> plus performant
    logger.info("SQL: Inserting or updating {} values in out db".format(len(rows)))
    st_execute = time.time()
    index = 0
    for i in range(math.ceil(len(rows)/10000)):
        tmp_rows = rows[i*10000:(i+1)*10000]
        values_str = ""
        for row in tmp_rows:
            values_str += "(%s, %s),"
        values_str = values_str[:-1]

        # Tuple des valeurs à insérer
        values_tuple = ()
        for row in tmp_rows:
            values_tuple += (row['id'], row['geom'])
            index += 1

        set_on_conflict = (
            "the_geom = excluded.the_geom"
        )

        sql_insert = """
            INSERT INTO ways_vertices_pgr (id, the_geom)
            VALUES {}
            ON CONFLICT (id) DO UPDATE
              SET {};
        """.format(values_str, set_on_conflict)
        cursor_out.execute(sql_insert, values_tuple)
        connection_out.commit()

    et_execute = time.time()
    logger.info("Writing vertices Done. Elapsed time : %s seconds." %(et_execute - st_execute))

    # Ways -----------------------------------------------------------------------------------------
    # Colonnes à lire dans la base source (champs classiques + champs servant aux coûts)
    attribute_columns = [
            'id',
            'geom',
            'source_id',
            'target_id',
            'x1',
            'y1',
            'x2',
            'y2',
            'ST_Length(geom) as length',
            'length_m as length_m',
            'importance as priority',
            'way_names as way_names',
            'nature as nature',
            'vitesse_moyenne_vl as vitesse_moyenne_vl',
            'position_par_rapport_au_sol as position_par_rapport_au_sol',
            'acces_vehicule_leger as acces_vehicule_leger'
        ]
    in_columns = attribute_columns.copy()
    for variable in costs["variables"]:
        in_columns += [variable["column_name"]]

    # Ecriture des ways
    sql_query = getQueryByTableAndBoundingBox('edges', resource['topology']['bbox'], in_columns)
    logger.info("SQL: {}".format(sql_query))
    st_execute = time.time()
    cursor_in.execute(sql_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    rows = cursor_in.fetchall()

    # Chaîne de n %s, pour l'insertion de données via psycopg
    single_value_str = "%s," * (len(attribute_columns) + 2 * len(costs["outputs"]))
    single_value_str = single_value_str[:-1]

    # Insertion petit à petit -> plus performant
    logger.info("SQL: Inserting or updating {} values in out db".format(len(rows)))
    st_execute = time.time()
    for i in range(math.ceil(len(rows)/10000)):
        tmp_rows = rows[i*10000:(i+1)*10000]
        # Chaîne permettant l'insertion de valeurs via psycopg
        values_str = ""
        for row in tmp_rows:
            values_str += "(" + single_value_str + "),"
        values_str = values_str[:-1]

        # Tuple des valuers à insérer
        values_tuple = ()
        for row in tmp_rows:
            output_costs = output_costs_from_costs_config(costs, row)
            values_tuple += (
                row['id'],
                row['geom'],
                row['source_id'],
                row['target_id'],
                row['x1'],
                row['y1'],
                row['x2'],
                row['y2'],
                row['length'],
                row['length_m'],
                row['priority'],
                row['way_names'],
                row['nature'],
                row['vitesse_moyenne_vl'],
                row['position_par_rapport_au_sol'],
                row['acces_vehicule_leger']
            ) + output_costs

        output_columns = (
            "(id, the_geom, source, target, x1, y1, x2, y2, length,"
            "length_m, priority, way_names, nature, vitesse_moyenne_vl, position_par_rapport_au_sol, acces_vehicule_leger"
        )
        set_on_conflict = (
            "the_geom = excluded.the_geom,source = excluded.source,target = excluded.target,"
            "x1 = excluded.x1,y1 = excluded.y1,x2 = excluded.x2,y2 = excluded.y2,"
            "length = excluded.length,length_m = excluded.length_m,priority = excluded.priority,"
            "way_names = excluded.way_names,nature = excluded.nature,vitesse_moyenne_vl = excluded.vitesse_moyenne_vl,"
            "position_par_rapport_au_sol = excluded.position_par_rapport_au_sol,acces_vehicule_leger = excluded.acces_vehicule_leger"
        )
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

    et_execute = time.time()
    logger.info("Writing ways ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    spacial_indices_query = """
        CREATE INDEX IF NOT EXISTS ways_geom_gist ON ways USING GIST (the_geom);
        CREATE INDEX IF NOT EXISTS vertices_geom_gist ON ways_vertices_pgr USING GIST (the_geom);
        CLUSTER ways USING ways_geom_gist ;
        CLUSTER ways_vertices_pgr USING vertices_geom_gist ;
    """
    logger.info("SQL: {}".format(spacial_indices_query))
    st_execute = time.time()
    cursor_out.execute(spacial_indices_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    connection_out.commit()

    old_isolation_level = connection_out.isolation_level
    connection_out.set_isolation_level(0)
    vacuum_query = "VACUUM ANALYZE;"
    logger.info("SQL: {}".format(vacuum_query))
    st_execute = time.time()
    cursor_out.execute(vacuum_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    connection_out.set_isolation_level(old_isolation_level)
    connection_out.commit()


    cursor_in.close()
    cursor_out.close()
    end_time = time.time()
    logger.info("Conversion for one cost from pivot to PGR ended. Elapsed time : %s seconds." %(end_time - start_time))
