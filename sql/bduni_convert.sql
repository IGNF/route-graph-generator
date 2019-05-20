-- ####################################################
-- IMPORT DE LA TABLE DES TRONCON DE ROUTE DEPUIS BDUNI
-- ####################################################

DROP SERVER IF EXISTS bduni_server CASCADE;
CREATE SERVER bduni_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host %(bdhost)s, port %(bdport)s, dbname %(dbname)s);

CREATE USER MAPPING FOR {user}
  SERVER bduni_server
  OPTIONS (user %(bduser)s, password %(bdpwd)s);

GRANT USAGE ON FOREIGN SERVER bduni_server TO {user};


DROP FOREIGN TABLE IF EXISTS troncon_de_route CASCADE;
DROP FOREIGN TABLE IF EXISTS route_numerotee_ou_nommee CASCADE;
DROP FOREIGN TABLE IF EXISTS non_communication CASCADE;
IMPORT FOREIGN SCHEMA public LIMIT TO (troncon_de_route, route_numerotee_ou_nommee, non_communication)
FROM SERVER bduni_server
INTO public;

-- ####################################
-- DEFINITION DU GRAPHE : NOEUDS / ARCS
-- ####################################
-- répétition du IF EXISTS pour ouvrir à l'éventualité de la mise à jour
DROP TABLE IF EXISTS nodes CASCADE ;
CREATE TABLE IF NOT EXISTS nodes (
  id bigserial primary key,
  lon double precision,
  lat double precision,
  geom geometry(Point,4326)
);

-- répétition du IF EXISTS pour ouvrir à l'éventualité de la mise à jour
DROP SEQUENCE IF EXISTS edges_id_seq;
CREATE SEQUENCE IF NOT EXISTS edges_id_seq;
DROP TABLE IF EXISTS edges;
CREATE TABLE IF NOT EXISTS edges (
  id bigserial primary key,
  source_id bigserial,
  target_id bigserial,
  length_m double precision,
  direction integer,
  geom geometry(Linestring,4326),
  -- Attributs spécifiques à la bd uni
  vitesse_moyenne_vl integer,
  nature text,
  cleabs text
);


CREATE INDEX IF NOT EXISTS nodes_geom_gist ON nodes USING GIST (geom);
CREATE INDEX IF NOT EXISTS nodes_lon_lat_idx ON nodes(lon,lat);
CREATE INDEX IF NOT EXISTS edges_geom_gist ON edges USING GIST (geom);

-- ####################################
-- UTILITAIRES DE REMPLISSAGE DU GRAPHE
-- ####################################

-- Renvoie le srid à partir du code territoire
CREATE OR REPLACE FUNCTION bduni_srid(code_territoire text) RETURNS int AS $$
BEGIN
  CASE
    WHEN (code_territoire = 'FXX') THEN
      RETURN 2154;
    WHEN (code_territoire = 'GLP') THEN
      RETURN 4559;
    WHEN (code_territoire = 'MTQ') THEN
      RETURN 4559;
    WHEN (code_territoire = 'GUF') THEN
      RETURN 2972;
    WHEN (code_territoire = 'REU') THEN
      RETURN 2975;
    WHEN (code_territoire = 'SPM') THEN
      RETURN 4467;
    WHEN (code_territoire = 'MYT') THEN
      RETURN 4471;
    ELSE
      RETURN NULL;
  END CASE;
END;
$$ LANGUAGE plpgsql;

-- Récupération d'un identifiant de sommet en fonction d'un point (égalité stricte)
CREATE OR REPLACE FUNCTION nodes_id( _geom geometry ) RETURNS bigint AS $$
  SELECT id FROM nodes WHERE lon = ST_X(_geom) AND lat = ST_Y(_geom);
$$ LANGUAGE SQL ;

-- Renvoie les points intermédiaires d'une linestring en format json
CREATE OR REPLACE FUNCTION inter_nodes(geom geometry(LineString, 4326)) RETURNS json[] AS $$
  SELECT COALESCE(array_agg(row_to_json(subq)), '{{}}') FROM (
    SELECT
      ST_X((dp).geom) AS lon,
      ST_Y((dp).geom) AS lat
    FROM (
      SELECT st_numpoints(geom) AS nump, ST_DumpPoints(geom) AS dp
    ) AS foo
    WHERE (dp).path[1] <@ int4range(2, nump)
  ) subq ;
$$ LANGUAGE SQL;

-- populate.sql
-- On doit copier au préalable troncon_de_route pour figer les tronçons car elle est mise à jour en continue

CREATE TEMP TABLE bduni_non_com_tmp AS
SELECT * FROM non_communication;


-- ############################
-- REMPLISSAGE DE BDUNI_TRONCON
-- ############################
-- Ajout des tronçons de routes (jointure avec routes numérotées et nommées)
CREATE TEMP TABLE IF NOT EXISTS bduni_troncon AS
  SELECT DISTINCT ON (cleabs) * FROM (
    SELECT
      -- GCVS (système d'historique)
      t.cleabs as cleabs,
      -- t.gcms_numrec as numrec,
      t.gcms_detruit AS detruit,
      t.gcms_territoire as territoire,

      -- BD TOPO
      -- NULLIF(t.etat_de_l_objet,'') as etat,
      -- n.type_de_route as cl_admin,
      t.nature as nature,
      t.importance as importance,
      -- t.fictif as fictif,
      -- t.position_par_rapport_au_sol as pos_sol,
      -- t.nombre_de_voies as nb_voies,
      t.sens_de_circulation as sens_de_circulation,
      -- t.itineraire_vert as it_vert,
      t.vitesse_moyenne_vl as vitesse_moyenne_vl,

      -- Pour l'attribut name
      t.nom_1_gauche as nom_g,
      t.nom_1_droite as nom_d,
      t.cpx_numero as cpx_numero,
      t.cpx_toponymie_route_nommee as cpx_toponyme,

      -- NULLIF(t.insee_commune_gauche,'') as inseecom_g,
      -- NULLIF(t.insee_commune_droite,'') as inseecom_d,
      -- t.largeur_de_chaussee as largeur,

      -- n.gestionnaire as gestion,
      -- n.numero as numero,

      -- NON BDTOPO
      NULLIF(n.cleabs,'') as rn_cleabs,

      -- NULLIF(t.acces,'') as acces,
      t.urbain as urbain,
      t.prive as prive,

      -- géométrie du troncon
      ST_Force2D(ST_Transform(ST_SetSrid(t.geometrie, bduni_srid(t.gcms_territoire)), 4326)) as geom

    FROM (
      -- decomposition liens_vers_route_nommee en lien_vers_route_nommee (split et duplication des lignes)
      SELECT t1.*, regexp_split_to_table( t1.liens_vers_route_nommee,'/') as lien_vers_route_nommee FROM troncon_de_route t1
    ) t
      LEFT JOIN route_numerotee_ou_nommee n
        -- gestion du lien multiple
        ON t.lien_vers_route_nommee = n.cleabs
  ) s
    WHERE NOT detruit
    AND geom && ST_MakeEnvelope(%(xmin)s,%(ymin)s,%(xmax)s,%(ymax)s, 4326 )
    -- décommenter pour tester :
    -- AND territoire='REU'
;

  -- ############################
  -- REMPLISSAGE DE nodes
  -- ############################
-- Remplissage de nodes avec les sommets initiaux et finaux des tronçons
-- (les points intermédiaires ne forment pas la topologie)
WITH t AS (
  SELECT ST_Force2D(ST_StartPoint(geom)) as geom FROM bduni_troncon
    UNION
  SELECT ST_Force2D(ST_EndPoint(geom)) as geom FROM bduni_troncon
)
INSERT INTO nodes (lon,lat,geom)
  SELECT ST_X(t.geom),ST_Y(t.geom),t.geom FROM t WHERE nodes_id(t.geom) IS NULL
;

-- ############################
-- REMPLISSAGE DE edges
-- ############################

INSERT INTO edges
  SELECT
    nextval('edges_id_seq') AS id,
    nodes_id(ST_StartPoint(geom)) as source_id,
    nodes_id(ST_EndPoint(geom)) as target_id,
    ST_length(geography(ST_Transform(geom, 4326))) as length_m,
    (CASE
      WHEN sens_de_circulation='Sens direct' THEN 1
      WHEN sens_de_circulation='Sens inverse' THEN -1
      ELSE 0
      END) as direction,
    geom as geom,
    -- Attributs spécifiques à la bd uni
    vitesse_moyenne_vl as vitesse_moyenne_vl,
    nature as nature,
    cleabs as cleabs,
    CONCAT(nom_g, '&&', nom_d, '&&', cpx_numero, '&&', cpx_toponyme) as way_names

  FROM bduni_troncon
;

-- ############################
-- REMPLISSAGE DE bduni_non_com
-- ############################

-- On ne conserve que les non communications sur la zone de calcul
DROP TABLE IF EXISTS non_comm;
CREATE TABLE IF NOT EXISTS non_comm AS
SELECT * FROM (
  SELECT
    cleabs,
    lien_vers_troncon_entree,
    -- liens_vers_troncon_sortie
    regexp_split_to_table(bduni_non_com_tmp.liens_vers_troncon_sortie, E'/') AS lien_vers_troncon_sortie
  FROM bduni_non_com_tmp
  WHERE lien_vers_troncon_entree IN (SELECT cleabs from edges)
) AS non_comm_split
WHERE non_comm_split.lien_vers_troncon_sortie IN (SELECT cleabs from edges);

-- Remplissage des ids d'edge dans la table des non communications
ALTER TABLE non_comm ADD COLUMN IF NOT EXISTS id_from bigint;
ALTER TABLE non_comm ADD COLUMN IF NOT EXISTS id_to bigint;

UPDATE non_comm AS b SET id_from = e.id
FROM edges as e
WHERE e.cleabs = b.lien_vers_troncon_entree
;

UPDATE non_comm AS b SET id_to = e.id
FROM edges as e
WHERE e.cleabs = b.lien_vers_troncon_sortie
;

-- Récupération du point commun entre deux troncons
CREATE OR REPLACE FUNCTION common_point(id_from bigint, id_to bigint) RETURNS bigint AS $$
  SELECT
  CASE
    WHEN a.source_id=b.source_id THEN b.source_id
    WHEN a.source_id=b.target_id THEN b.target_id
    WHEN a.target_id=b.source_id THEN b.source_id
    WHEN a.target_id=b.target_id THEN b.target_id
    ELSE -1
  END
  FROM edges as a, edges as b
  WHERE a.id = id_from
  AND b.id = id_to;
$$ LANGUAGE SQL ;

ALTER TABLE non_comm ADD COLUMN IF NOT EXISTS common_vertex_id bigint;
UPDATE non_comm SET common_vertex_id = common_point(non_comm.id_from, non_comm.id_to);

END TRANSACTION;
VACUUM ANALYZE;
