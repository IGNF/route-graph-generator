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

DROP TABLE IF EXISTS bduni_vertex CASCADE ;
CREATE TABLE bduni_vertex (
    id serial primary key,
    lon float,
    lat float,
    -- ajouter ce qui est utile pour OSRM...
    geom geometry(Point,4326)
);
CREATE INDEX bduni_vertex_geom_gist ON bduni_vertex USING GIST (geom);
CREATE INDEX bduni_vertex_lon_lat_idx ON bduni_vertex(lon,lat);


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
CREATE OR REPLACE FUNCTION bduni_vertex_id( _geom geometry ) RETURNS integer AS $$
    SELECT id FROM bduni_vertex WHERE lon = ST_X(_geom) AND lat = ST_Y(_geom);
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
DROP TABLE IF EXISTS bduni_troncon;
CREATE TABLE bduni_troncon AS
    SELECT DISTINCT ON (cleabs) * FROM (
      SELECT
        -- GCVS (système d'historique)
        t.cleabs as cleabs,
        t.gcms_numrec as numrec,
        t.gcms_detruit AS detruit,
        t.gcms_territoire as territoire,

        -- BD TOPO
        NULLIF(t.etat_de_l_objet,'') as etat,
        n.type_de_route as cl_admin,
        t.nature as nature,
        t.importance as importance,
        t.fictif as fictif,
        t.position_par_rapport_au_sol as pos_sol,
        t.nombre_de_voies as nb_voies,
        t.sens_de_circulation as sens_de_circulation,
        t.itineraire_vert as it_vert,
        -- NULLIF(t.nom_rue_gauche,'') as nom_voie_g,
        -- NULLIF(t.nom_rue_droite,'') as nom_voie_d,
        NULLIF(t.insee_commune_gauche,'') as inseecom_g,
        NULLIF(t.insee_commune_droite,'') as inseecom_d,
        t.largeur_de_chaussee as largeur,

        n.gestionnaire as gestion,
        n.numero as numero,

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
  -- décommenter pour tester :
  AND territoire='MTQ'
  ;

  -- ############################
  -- REMPLISSAGE DE BDUNI_VERTEX
  -- ############################
-- Remplissage de bduni_vertex avec les sommets initiaux et finaux des tronçons
-- (les points intermédiaires ne forment pas la topologie)
WITH t AS (
  SELECT ST_Force2D(ST_StartPoint(geom)) as geom FROM bduni_troncon
    UNION
  SELECT ST_Force2D(ST_EndPoint(geom)) as geom FROM bduni_troncon
)
INSERT INTO bduni_vertex (lon,lat,geom)
  SELECT ST_X(t.geom),ST_Y(t.geom),t.geom FROM t WHERE bduni_vertex_id(t.geom) IS NULL
;

-- ############################
-- REMPLISSAGE DE BDUNI_EDGE
-- ############################
DROP SEQUENCE IF EXISTS bduni_edge_id_seq;
CREATE SEQUENCE bduni_edge_id_seq;
DROP TABLE IF EXISTS bduni_edge;
CREATE TABLE bduni_edge AS
SELECT
  nextval('bduni_edge_id_seq') AS id,
  bduni_vertex_id(ST_StartPoint(geom)) as source_id,
  bduni_vertex_id(ST_EndPoint(geom)) as target_id,
  (CASE
    WHEN sens_de_circulation='Sens direct' THEN 1
    WHEN sens_de_circulation='Sens inverse' THEN -1
    ELSE 0
    END) as direction,

  * -- TODO ne mettre que les attributs nécessaires
FROM bduni_troncon
;

-- ############################
-- REMPLISSAGE DE bduni_non_com
-- ############################

-- TODO : Si on veut être complet il faudrait renormaliser la table des non_comm en splittant le champ liens_vers_troncon_sortie
--SELECT
--    yourTable.ID,
--    regexp_split_to_table(yourTable.fruits, E'&') AS split_fruits
--FROM yourTable


-- On ne conserve que les non communications sur la zone de calcul
DROP TABLE IF EXISTS bduni_non_com;
CREATE TABLE bduni_non_com AS
SELECT
  cleabs, lien_vers_troncon_entree, liens_vers_troncon_sortie
FROM bduni_non_com_tmp
-- WHERE geometrie && ST_Transform( ST_SetSRID( ST_MakeEnvelope(:bbox),4326 ),2154 )
 WHERE lien_vers_troncon_entree in (SELECT cleabs from bduni_edge)
 AND liens_vers_troncon_sortie in (SELECT cleabs from bduni_edge)
;


-- Remplissage des ids d'edge dans la table des non communications
ALTER TABLE bduni_non_com ADD COLUMN id_from bigint;
ALTER TABLE bduni_non_com ADD COLUMN id_to bigint;

UPDATE bduni_non_com AS b SET id_from = e.id
FROM bduni_edge as e
WHERE e.cleabs = b.lien_vers_troncon_entree
;

UPDATE bduni_non_com AS b SET id_to = e.id
FROM bduni_edge as e
WHERE e.cleabs = b.liens_vers_troncon_sortie
;

-- Récupération du point commun entre deux troncons
CREATE OR REPLACE FUNCTION common_point(id_from bigint, id_to bigint) RETURNS integer AS $$
  SELECT
  CASE
     WHEN a.source_id=b.source_id THEN b.source_id
     WHEN a.source_id=b.target_id THEN b.target_id
     WHEN a.target_id=b.source_id THEN b.source_id
     WHEN a.target_id=b.target_id THEN b.target_id
     ELSE 0
  END
  FROM bduni_edge as a, bduni_edge as b
  WHERE a.id = id_from
  AND b.id = id_to;
$$ LANGUAGE SQL ;

ALTER TABLE bduni_non_com ADD COLUMN common_vertex_id integer;
UPDATE bduni_non_com SET common_vertex_id = common_point(bduni_non_com.id_from, bduni_non_com.id_to);
