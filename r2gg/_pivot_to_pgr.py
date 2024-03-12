import math
import time
import sys

from psycopg2.extras import DictCursor

from r2gg._output_costs_from_costs_config import output_costs_from_costs_config
from r2gg._read_config import config_from_path
from r2gg._sql_building import getQueryByTableAndBoundingBox

def pivot_to_pgr(source, cost_calculation_file_path, connection_work, connection_out, schema, input_schema, logger):
    """
    Fonction de conversion depuis la bdd pivot vers la base pgr

    Parameters
    ----------
    source: dict
    cost_calculation_file_path: str
        chemin vers le fichier json de configuration des coûts
    connection_work: psycopg2.connection
        connection à la bdd de travail
    connection_out: psycopg2.connection
        connection à la bdd pgrouting de sortie
    schema: str
        nom du schéma dans la base de sortie
    input_schema: str
        nom du schéma dans la base en entrée
    logger: logging.Logger
    """

    cursor_in = connection_work.cursor(cursor_factory=DictCursor, name="cursor_in")
    ways_table_name = schema + '.ways'
    # Récupération des coûts à calculer
    costs = config_from_path(cost_calculation_file_path)

    cursor_out = connection_out.cursor()
    # Création de la edge_table pgrouting
    create_table = """
        DROP TABLE IF EXISTS {0};
        CREATE TABLE {0}(
            id bigserial unique,
            tag_id integer,
            length double precision,
            length_m double precision,
            name text,
            source bigint,
            target bigint,
            x1 double precision,
            y1 double precision,
            x2 double precision,
            y2 double precision,
            importance double precision DEFAULT 6,
            the_geom geometry(Linestring,4326),
            cleabs text,
            nom_1_gauche text,
            nom_1_droite text,
            cpx_numero text,
            cpx_toponyme_route_nommee text,
            nature text,
            vitesse_moyenne_vl integer,
            position_par_rapport_au_sol integer,
            acces_vehicule_leger text,
            largeur_de_chaussee double precision,
            nombre_de_voies text,
            insee_commune_gauche text,
            insee_commune_droite text,
            bande_cyclable text,
            itineraire_vert boolean,
            sens_de_circulation text,
            reserve_aux_bus text,
            urbain boolean,
            acces_pieton text,
            nature_de_la_restriction text,
            restriction_de_hauteur double precision,
            restriction_de_poids_total double precision,
            restriction_de_poids_par_essieu double precision,
            restriction_de_largeur double precision,
            restriction_de_longueur double precision,
            matieres_dangereuses_interdites boolean,
            cpx_gestionnaire text,
            cpx_numero_route_europeenne text,
            cpx_classement_administratif text
        );""".format(ways_table_name)
    logger.debug("SQL: {}".format(create_table))
    cursor_out.execute(create_table)

    # Ajout des colonnes de coûts
    add_columns = "ALTER TABLE {} ".format(ways_table_name)
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
        DROP TABLE IF EXISTS {0}.turn_restrictions;
        CREATE TABLE {0}.turn_restrictions(
            id bigserial unique,
            id_from bigint,
            id_to bigint
    );""".format(schema)
    logger.debug("SQL: {}".format(create_non_comm))
    cursor_out.execute(create_non_comm)

    logger.info("Populating turn restrictions")
    tr_query = f"SELECT id_from, id_to FROM {input_schema}.non_comm;"

    logger.debug("SQL: {}".format(tr_query))
    st_execute = time.time()
    cursor_in.execute(tr_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    # Insertion petit à petit -> plus performant
    logger.info("SQL: Inserting or updating {} values in out db".format(cursor_in.rowcount))
    st_execute = time.time()
    index = 0
    batchsize = 10000
    rows = cursor_in.fetchmany(batchsize)
    while rows:
        values_str = ""
        for row in rows:
            values_str += "(%s, %s, %s),"
        values_str = values_str[:-1]

        # Tuple des valuers à insérer
        values_tuple = ()
        for row in rows:
            values_tuple += (index, row['id_from'], row['id_to'])
            index += 1

        set_on_conflict = (
            "id_from = excluded.id_from,id_to = excluded.id_to"
        )

        sql_insert = """
            INSERT INTO {}.turn_restrictions (id, id_from, id_to)
            VALUES {}
            ON CONFLICT (id) DO UPDATE
              SET {};
        """.format(schema, values_str, set_on_conflict)
        cursor_out.execute(sql_insert, values_tuple)
        connection_out.commit()
        rows = cursor_in.fetchmany(batchsize)

    et_execute = time.time()
    cursor_in.close()
    logger.info("Writing turn restrinctions Done. Elapsed time : %s seconds." %(et_execute - st_execute))

    # Noeuds ---------------------------------------------------------------------------------------
    logger.info("Writing vertices...")
    cursor_in = connection_work.cursor(cursor_factory=DictCursor, name="cursor_in")
    create_nodes = """
        DROP TABLE IF EXISTS {0}_vertices_pgr;
        CREATE TABLE {0}_vertices_pgr(
            id bigserial unique,
            cnt int,
            chk int,
            ein int,
            eout int,
            the_geom geometry(Point,4326)
    );""".format(ways_table_name)
    logger.debug("SQL: {}".format(create_nodes))
    cursor_out.execute(create_nodes)

    logger.info("Populating vertices")
    nd_query = f"SELECT id, geom FROM {input_schema}.nodes;"

    logger.debug("SQL: {}".format(nd_query))
    st_execute = time.time()
    cursor_in.execute(nd_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    # Insertion petit à petit -> plus performant
    # logger.info("SQL: Inserting or updating {} values in out db".format(cursor_in.rowcount))
    st_execute = time.time()
    index = 0
    batchsize = 10000
    rows = cursor_in.fetchmany(batchsize)
    while rows:
        values_str = ""
        for row in rows:
            values_str += "(%s, %s),"
        values_str = values_str[:-1]

        # Tuple des valeurs à insérer
        values_tuple = ()
        for row in rows:
            values_tuple += (row['id'], row['geom'])
            index += 1

        set_on_conflict = (
            "the_geom = excluded.the_geom"
        )

        sql_insert = """
            INSERT INTO {}_vertices_pgr (id, the_geom)
            VALUES {}
            ON CONFLICT (id) DO UPDATE
              SET {};
        """.format(ways_table_name, values_str, set_on_conflict)
        cursor_out.execute(sql_insert, values_tuple)
        connection_out.commit()
        rows = cursor_in.fetchmany(batchsize)


    et_execute = time.time()
    cursor_in.close()
    logger.info("Writing vertices Done. Elapsed time : %s seconds." %(et_execute - st_execute))

    # Ways -----------------------------------------------------------------------------------------
    # Colonnes à lire dans la base source (champs classiques + champs servant aux coûts)
    cursor_in = connection_work.cursor(cursor_factory=DictCursor, name="cursor_in")
    attribute_columns = [
            'id',
            'geom as the_geom',
            'source_id as source',
            'target_id as target',
            'x1',
            'y1',
            'x2',
            'y2',
            'ST_Length(geom) as length',
            'length_m as length_m',
            'cleabs as cleabs',
            'importance as importance',
            'nature as nature',
            'nom_1_gauche as nom_1_gauche',
            'nom_1_droite as nom_1_droite',
            'cpx_numero as cpx_numero',
            'cpx_toponyme_route_nommee as cpx_toponyme_route_nommee',
            'vitesse_moyenne_vl as vitesse_moyenne_vl',
            'position_par_rapport_au_sol as position_par_rapport_au_sol',
            'acces_vehicule_leger as acces_vehicule_leger',
            'largeur_de_chaussee as largeur_de_chaussee',
            'nombre_de_voies as nombre_de_voies',
            'insee_commune_gauche as insee_commune_gauche',
            'insee_commune_droite as insee_commune_droite',
            'bande_cyclable as bande_cyclable',
            'itineraire_vert as itineraire_vert',
            'sens_de_circulation as sens_de_circulation',
            'reserve_aux_bus as reserve_aux_bus',
            'urbain as urbain',
            'acces_pieton as acces_pieton',
            'nature_de_la_restriction as nature_de_la_restriction',
            'restriction_de_hauteur as restriction_de_hauteur',
            'restriction_de_poids_total as restriction_de_poids_total',
            'restriction_de_poids_par_essieu as restriction_de_poids_par_essieu',
            'restriction_de_largeur as restriction_de_largeur',
            'restriction_de_longueur as restriction_de_longueur',
            'matieres_dangereuses_interdites as matieres_dangereuses_interdites',
            'cpx_gestionnaire as cpx_gestionnaire',
            'cpx_numero_route_europeenne as cpx_numero_route_europeenne',
            'cpx_classement_administratif as cpx_classement_administratif'
        ]
    in_columns = attribute_columns.copy()
    for variable in costs["variables"]:
        in_columns += [variable["column_name"]]

    output_columns_names = [column.split(' ')[-1] for column in attribute_columns]

    # Ecriture des ways
    sql_query = getQueryByTableAndBoundingBox(f'{input_schema}.edges', source['bbox'], in_columns)
    logger.info("SQL: {}".format(sql_query))
    st_execute = time.time()
    cursor_in.execute(sql_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    # Chaîne de n %s, pour l'insertion de données via psycopg
    single_value_str = "%s," * (len(attribute_columns) + 2 * len(costs["outputs"]))
    single_value_str = single_value_str[:-1]

    # Insertion petit à petit -> plus performant
    # logger.info("SQL: Inserting or updating {} values in out db".format(cursor_in.rowcount))
    st_execute = time.time()
    batchsize = 10000
    percent = 0
    rows = cursor_in.fetchmany(batchsize)
    while rows:
        percent += 1000000 / cursor_in.rowcount
        # Chaîne permettant l'insertion de valeurs via psycopg
        values_str = ""
        for row in rows:
            values_str += "(" + single_value_str + "),"
        values_str = values_str[:-1]

        # Tuple des valuers à insérer
        values_tuple = ()
        for row in rows:
            output_costs = output_costs_from_costs_config(costs, row)
            values_tuple += tuple(
                row[ output_columns_name ] for output_columns_name in output_columns_names
            ) + output_costs

        output_columns = "("
        for output_columns_name in output_columns_names:
            output_columns += output_columns_name + ','
        output_columns = output_columns[:-1]

        set_on_conflict = ''
        for output_columns_name in output_columns_names:
            set_on_conflict += "{0} = excluded.{0},".format(output_columns_name)
        set_on_conflict = set_on_conflict[:-1]

        for output in costs["outputs"]:
            output_columns += "," + output["name"] + ",reverse_" + output["name"]
            set_on_conflict += ",{0} = excluded.{0}".format(output["name"])
            set_on_conflict += ",{0} = excluded.{0}".format("reverse_" + output["name"])

        output_columns += ")"
        sql_insert = """
            INSERT INTO {} {}
            VALUES {}
            ON CONFLICT (id) DO UPDATE
              SET {};
            """.format(ways_table_name, output_columns, values_str, set_on_conflict)
        cursor_out.execute(sql_insert, values_tuple)
        connection_out.commit()
        rows = cursor_in.fetchmany(batchsize)

    et_execute = time.time()
    cursor_in.close();
    logger.info("Writing ways ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    spacial_indices_query = """
        CREATE INDEX IF NOT EXISTS ways_geom_gist ON {0} USING GIST (the_geom);
        CREATE INDEX IF NOT EXISTS ways_vertices_geom_gist ON {0}_vertices_pgr USING GIST (the_geom);
        CLUSTER {0} USING ways_geom_gist ;
        CLUSTER {0}_vertices_pgr USING ways_vertices_geom_gist ;
        CREATE INDEX IF NOT EXISTS ways_importance_idx ON {0} USING btree (importance);
    """.format(ways_table_name)
    logger.info("SQL: {}".format(spacial_indices_query))
    st_execute = time.time()
    cursor_out.execute(spacial_indices_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    connection_out.commit()

    turn_restrictions_indices_query = """
        CREATE INDEX IF NOT EXISTS turn_restrictions_id_key ON {0}.turn_restrictions USING btree (id);
        CREATE INDEX IF NOT EXISTS ways_id_key ON {1} USING btree (id);
        CREATE INDEX IF NOT EXISTS ways_vertices_pgr_id_key ON {1}_vertices_pgr USING btree (id);
    """.format(schema, ways_table_name)
    logger.info("SQL: {}".format(turn_restrictions_indices_query))
    st_execute = time.time()
    cursor_out.execute(turn_restrictions_indices_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    connection_out.commit()

    old_isolation_level = connection_out.isolation_level
    connection_out.set_isolation_level(0)

    # VACCUM ANALYZE for ways
    vacuum_query = f"VACUUM ANALYZE {ways_table_name};"
    logger.info("SQL: {}".format(vacuum_query))
    st_execute = time.time()
    cursor_out.execute(vacuum_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    # VACCUM ANALYZE for ways_vertices_pgr
    vacuum_query = f"VACUUM ANALYZE {ways_table_name}_vertices_pgr;"
    logger.info("SQL: {}".format(vacuum_query))
    st_execute = time.time()
    cursor_out.execute(vacuum_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    # VACCUM ANALYZE for turn_restrictions
    vacuum_query = f"VACUUM ANALYZE {schema}.turn_restrictions;"
    logger.info("SQL: {}".format(vacuum_query))
    st_execute = time.time()
    cursor_out.execute(vacuum_query)
    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))

    connection_out.set_isolation_level(old_isolation_level)
    connection_out.commit()

    cursor_out.close()

    # Nettoyage du graphe
    logger.info("Cleaning isolated clusters of less than 10 edges...")
    cursor_isolated = connection_out.cursor()

    profile_names = set([ cost['profile'] for cost in source["costs"]])
    st_execute = time.time()

    for profile_name in profile_names:
        logger.info("Cleaning isolated edges for profile {}...".format(profile_name))
        clean_graph_query = """
        WITH connected_components AS (
          SELECT * FROM pgr_connectedComponents(
            'SELECT id, source, target, cost_s_{1} as cost, reverse_cost_s_{1} as reverse_cost FROM {0}.ways'
          )
        ),
        remove_nodes AS (
          SELECT node
          FROM
            connected_components
          WHERE
          component = ANY(
            SELECT DISTINCT component
            FROM
            (
              SELECT component, count(*) AS nb
              FROM
                connected_components
              GROUP BY component
            )
            AS components
            WHERE nb <= 10
          )
        )
        UPDATE {0}.ways
        SET cost_s_{1} = -1,
          reverse_cost_s_{1} = -1,
          cost_m_{1} = -1,
          reverse_cost_m_{1} = -1
        WHERE {0}.ways.target = ANY(SELECT * from remove_nodes) OR {0}.ways.source = ANY(SELECT * from remove_nodes);
        """.format(schema, profile_name)
        logger.info("SQL: {}".format(clean_graph_query))
        cursor_isolated.execute(clean_graph_query)
        connection_out.commit()

    et_execute = time.time()
    logger.info("Execution ended. Elapsed time : %s seconds." %(et_execute - st_execute))
    cursor_isolated.close()

    end_time = time.time()
    logger.info("Conversion from pivot to PGR ended. Elapsed time : %s seconds." %(end_time - start_time))
