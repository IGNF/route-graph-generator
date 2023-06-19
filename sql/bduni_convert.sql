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


CREATE SCHEMA IF NOT EXISTS {output_schema};

DROP FOREIGN TABLE IF EXISTS {output_schema}.troncon_de_route CASCADE;
DROP FOREIGN TABLE IF EXISTS {output_schema}.non_communication CASCADE;

IMPORT FOREIGN SCHEMA {input_schema} LIMIT TO (troncon_de_route, non_communication, bduni_verrouillage)
FROM SERVER bduni_server
INTO {output_schema};

-- ####################################
-- DEFINITION DU GRAPHE : NOEUDS / ARCS
-- ####################################
-- répétition du IF EXISTS pour ouvrir à l'éventualité de la mise à jour
DROP TABLE IF EXISTS {output_schema}.nodes CASCADE ;
CREATE TABLE IF NOT EXISTS {output_schema}.nodes (
  id bigserial primary key,
  lon double precision,
  lat double precision,
  geom geometry(Point,4326)
);

-- répétition du IF EXISTS pour ouvrir à l'éventualité de la mise à jour
DROP SEQUENCE IF EXISTS {output_schema}.edges_id_seq;
CREATE SEQUENCE IF NOT EXISTS {output_schema}.edges_id_seq;
DROP TABLE IF EXISTS {output_schema}.edges;
CREATE TABLE IF NOT EXISTS {output_schema}.edges (
  id bigserial primary key,
  source_id bigserial,
  target_id bigserial,
  x1 double precision,
  y1 double precision,
  x2 double precision,
  y2 double precision,
  length_m double precision,
  direction integer,
  geom geometry(Linestring,4326),
  -- Attributs spécifiques à la bd uni
  vitesse_moyenne_vl integer,
  nature text,
  cleabs text,
  importance integer,
  way_names text,
  nom_1_gauche text,
  nom_1_droite text,
  cpx_numero text,
  cpx_toponyme_route_nommee text,
  sens_de_circulation text,
  position_par_rapport_au_sol integer,
  acces_vehicule_leger text,
  largeur_de_chaussee double precision,
  nombre_de_voies text,
  insee_commune_gauche text,
  insee_commune_droite text,
  bande_cyclable text,
  itineraire_vert boolean,
  reserve_aux_bus text,
  urbain boolean,
  acces_pieton text,
  nature_de_la_restriction text,
  restriction_de_hauteur text,
  restriction_de_poids_total text,
  restriction_de_poids_par_essieu text,
  restriction_de_largeur text,
  restriction_de_longueur text,
  matieres_dangereuses_interdites boolean,
  cpx_gestionnaire text,
  cpx_numero_route_europeenne text,
  cpx_classement_administratif text
);


CREATE INDEX IF NOT EXISTS nodes_geom_gist ON {output_schema}.nodes USING GIST (geom);
CREATE INDEX IF NOT EXISTS nodes_lon_lat_idx ON {output_schema}.nodes(lon,lat);
CREATE INDEX IF NOT EXISTS edges_geom_gist ON {output_schema}.edges USING GIST (geom);

-- ####################################
-- UTILITAIRES DE REMPLISSAGE DU GRAPHE
-- ####################################

-- Renvoie le srid à partir du code territoire
CREATE OR REPLACE FUNCTION {output_schema}.bduni_srid(code_territoire text) RETURNS int AS $$
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
CREATE OR REPLACE FUNCTION {output_schema}.nodes_id( _geom geometry ) RETURNS bigint AS $$
  SELECT id FROM {output_schema}.nodes WHERE lon = ST_X(_geom) AND lat = ST_Y(_geom);
$$ LANGUAGE SQL ;

-- Renvoie les points intermédiaires d'une linestring en format json
CREATE OR REPLACE FUNCTION {output_schema}.inter_nodes(geom geometry(LineString, 4326)) RETURNS json[] AS $$
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
SELECT * FROM {output_schema}.non_communication;

-- rattachement des tronçons aux frontières pour éviter la perte d'itinéraires (impasses à sens unique)
-- OSRM supprime les impasses à sens unique de ses itinéraires
-- Aux frontières, les autoroutes (2 tronçons car 2 chaussées) sont coupées abruptement, créant ce type d'impasse
-- Cette fonction rattache les 2 tronçons des autoroutes après la frontière avec un tronçon fictif
-- Cela correspond à 19 cas sur la france entière.
CREATE OR REPLACE FUNCTION {output_schema}.liaison_fictive_chor_frontaliere()
RETURNS TABLE(
  cleabs character varying, nature character varying, nom_1_gauche character varying, nom_1_droite character varying, nom_2_gauche character varying, nom_2_droite character varying, importance character varying, fictif boolean, position_par_rapport_au_sol character varying, etat_de_l_objet character varying, gcms_detruit boolean, gcms_date_creation timestamp without time zone, gcms_date_modification timestamp without time zone, gcms_date_destruction timestamp without time zone, date_d_apparition date, date_de_confirmation date, diffusion boolean, source_detaillee jsonb, sources character varying, identifiants_sources character varying, methode_d_acquisition_planimetrique character varying, precision_planimetrique numeric, methode_d_acquisition_altimetrique character varying, precision_altimetrique numeric, complement jsonb, nombre_de_voies character varying, largeur_de_chaussee numeric, itineraire_vert boolean, prive boolean, sens_de_circulation character varying, bande_cyclable character varying, reserve_aux_bus character varying, urbain boolean, vitesse_moyenne_vl integer, acces_vehicule_leger character varying, acces_pieton character varying, periode_de_fermeture jsonb, nature_de_la_restriction character varying, restriction_de_hauteur numeric, restriction_de_poids_total numeric, restriction_de_poids_par_essieu numeric, restriction_de_largeur numeric, restriction_de_longueur numeric, matieres_dangereuses_interdites boolean, borne_debut_gauche character varying, borne_debut_droite character varying, borne_fin_gauche character varying, borne_fin_droite character varying, insee_commune_gauche character varying, insee_commune_droite character varying, type_d_adressage_du_troncon character varying, alias_gauche character varying, alias_droit character varying, code_postal_gauche character varying, code_postal_droit character varying, itineraire_pedestre boolean, itineraire_equestre boolean, inscrit_au_pdipr boolean, bornes_debut_interpolees boolean, bornes_fin_interpolees boolean, nom_rue_gauche_valide date, nom_rue_droite_valide date, bornes_postales_validees date, nom character varying, commentaire_centralise character varying, commentaire_collecteur character varying, date_de_mise_en_service date, source_restitution character varying, metadonnees_guichet_adresse character varying, identifiant_voie_1_gauche character varying, identifiant_voie_1_droite character varying, liens_vers_evolution character varying, liens_vers_route_nommee character varying, liens_vers_itineraire_ffr character varying, liens_vers_itineraire_club_vosgien character varying, liens_vers_itineraire_autre character varying, gcms_numrec integer, gcms_territoire character varying, gcms_fingerprint character varying, gcvs_nom_lot character varying, exception_legitime character varying, affichage_rue boolean, cpx_numero character varying, cpx_numero_route_europeenne character varying, cpx_classement_administratif character varying, cpx_gestionnaire character varying, cpx_toponyme_route_nommee character varying, cpx_toponyme_itineraire_cyclable character varying, cpx_toponyme_voie_verte character varying, cpx_nature_itineraire_ffr character varying, cpx_toponyme_itineraire_ffr character varying, cpx_balisage_itineraire_club_vosgien character varying, cpx_toponyme_itineraire_club_vosgien character varying, cpx_nature_itineraire_autre character varying, cpx_toponyme_itineraire_autre character varying, geometrie geometry, gcvs_empreinte geometry, couloir_de_bus character varying, delestage boolean, liens_vers_prescriptions_te character varying, source_voie_ban_gauche character varying, source_voie_ban_droite character varying, nom_voie_ban_gauche character varying, nom_voie_ban_droite character varying, lieux_dits_ban_gauche character varying, lieux_dits_ban_droite character varying, identifiant_voie_ban_gauche character varying, identifiant_voie_ban_droite character varying, code_insee_du_departement_te character varying, reseau_te character varying, identifiant_te character varying, sens_amenagement_cyclable_gauche character varying, sens_amenagement_cyclable_droit character varying, amenagement_cyclable_gauche character varying, amenagement_cyclable_droit character varying
)
AS $$
BEGIN
  DROP TABLE IF EXISTS extr;
  CREATE TEMP TABLE extr as
  --selection des extrémités des troncon_de_route de la table bduni_verrouillage on ne conserve que les valences 1 (extrémités pendantes)
  SELECT a.cleabs, a.geom, a.extr FROM
  (SELECT min(a.cleabs) as cleabs, st_force2d(geom) as geom, min(extr) as extr FROM
    (SELECT t.cleabs, ST_StartPoint(t.geometrie) geom, 'start' as extr
      FROM troncon_de_route t,
      (SELECT t.* FROM troncon_de_route t WHERE t.cleabs IN (SELECT v.cleabs FROM bduni_verrouillage v WHERE v.processus = 'itin_geoportail' AND v.id > 4107280))b
        WHERE not t.gcms_detruit AND t.nature IN('Type autoroutier','Route à 2 chaussées') AND ST_Intersects(t.geometrie, b.geometrie)
    UNION ALL
    SELECT t.cleabs, ST_EndPoint(t.geometrie), 'end'
      FROM troncon_de_route t,
      (SELECT t.* FROM troncon_de_route t WHERE t.cleabs IN (SELECT v.cleabs FROM bduni_verrouillage v WHERE v.processus = 'itin_geoportail' AND v.id > 4107280))b
        WHERE not t.gcms_detruit AND t.nature IN('Type autoroutier','Route à 2 chaussées') AND ST_Intersects(t.geometrie, b.geometrie)
  ) a
  GROUP BY st_force2d(geom) HAVING count(*) = 1
  ) a
  WHERE a.cleabs IN (SELECT v.cleabs FROM bduni_verrouillage v WHERE v.processus = 'itin_geoportail' AND v.id > 4107280);
  --Génération de la table des points initiaux
  DROP TABLE IF EXISTS ptini;
  CREATE TEMP TABLE ptini as
  SELECT a.cleabs, ST_Translate(a.geom,0,0,-1000) as geom FROM extr a WHERE a.extr = 'start';
  --Génération de la table des points finaux
  DROP TABLE IF EXISTS ptfin;
  CREATE TEMP TABLE ptfin as
  SELECT a.cleabs, ST_Translate(a.geom,0,0,-1000) as geom  FROM extr a WHERE a.extr = 'end';
  --Création de la liaison géométrie dépourvue de Z (-1000), affectation d'une cleabs non bduni mais de même format
  DROP TABLE IF EXISTS calc;
  CREATE TEMP TABLE calc as
  SELECT rpad('TRONROUT',24-length(Row_Number() Over()::text),'0')||Row_Number() Over()::varchar(24) as cleabs,
  c.cleabs as cleabs_ini, st_translate(st_force3d(st_force2d(ST_Makeline(b.geom, a.geom))),0,0,-1000)::geometry(LinestringZ) as geometrie
  FROM ptini a, ptfin b, troncon_de_route c
  WHERE ST_DWithin(a.geom,b.geom,100)
  AND a.cleabs = c.cleabs;
  --On propage tous les attributs des chaussées à étendre
  DROP TABLE IF EXISTS jonction_fictive_chaussor;
  CREATE TEMP TABLE jonction_fictive_chaussor as
  SELECT t.*
  FROM troncon_de_route t WHERE t.cleabs IN(SELECT a.cleabs FROM ptini a);
  UPDATE jonction_fictive_chaussor a SET geometrie = b.geometrie, cleabs = b.cleabs
  FROM calc b WHERE a.cleabs = b.cleabs_ini;
  RETURN QUERY SELECT * FROM jonction_fictive_chaussor;
    DROP TABLE extr;
    DROP TABLE ptini;
    DROP TABLE ptfin;
    DROP TABLE calc;
    DROP TABLE jonction_fictive_chaussor;
END
$$ LANGUAGE plpgsql ;


-- ############################
-- REMPLISSAGE DE BDUNI_TRONCON
-- ############################
-- Ajout des tronçons de routes (jointure avec routes numérotées et nommées)
CREATE TEMP TABLE IF NOT EXISTS bduni_troncon AS
  SELECT DISTINCT ON (cleabs) * FROM (
    SELECT
      -- GCVS (système d'historique)
      t.cleabs as cleabs,
      t.gcms_detruit AS detruit,
      t.gcms_territoire as territoire,

      -- BD TOPO
      t.etat_de_l_objet as etat,
      t.nature as nature,
      NULLIF(t.importance,'')::int as importance,
      t.sens_de_circulation as sens_de_circulation,
      (CASE
      WHEN t.vitesse_moyenne_vl=1 THEN 0
      ELSE t.vitesse_moyenne_vl::integer
      END) as vitesse_moyenne_vl,

      -- Pour l'attribut name
      -- TODO: nom_collaboratif_gauche
      t.nom_1_gauche as nom_1_gauche,
      -- TODO: nom_collaboratif_droite
      t.nom_1_droite as nom_1_droite,
      t.cpx_numero as cpx_numero,
      t.cpx_toponyme_route_nommee as cpx_toponyme,

      (CASE
      WHEN t.position_par_rapport_au_sol='Gué ou radier' THEN 0
      ELSE t.position_par_rapport_au_sol::integer
      END) as position_par_rapport_au_sol,
      t.acces_vehicule_leger as acces_vehicule_leger,

      t.largeur_de_chaussee as largeur_de_chaussee,

      -- Champs demandés par la DP
      t.itineraire_vert as itineraire_vert,
      t.nombre_de_voies as nombre_de_voies,
      t.insee_commune_gauche as insee_commune_gauche,
      t.insee_commune_droite as insee_commune_droite,
      -- TODO: remove
      t.bande_cyclable as bande_cyclable,
      t.reserve_aux_bus as reserve_aux_bus,
      t.urbain as urbain,
      t.acces_pieton as acces_pieton,
      t.nature_de_la_restriction as nature_de_la_restriction,
      t.restriction_de_hauteur as restriction_de_hauteur,
      t.restriction_de_poids_total as restriction_de_poids_total,
      t.restriction_de_poids_par_essieu as restriction_de_poids_par_essieu,
      t.restriction_de_largeur as restriction_de_largeur,
      t.restriction_de_longueur as restriction_de_longueur,
      t.matieres_dangereuses_interdites as matieres_dangereuses_interdites,
      t.cpx_gestionnaire as cpx_gestionnaire,
      t.cpx_numero_route_europeenne as cpx_numero_route_europeenne,
      t.cpx_classement_administratif as cpx_classement_administratif,

      -- géométrie du troncon
      ST_Force2D(ST_Transform(ST_SetSrid(t.geometrie, {output_schema}.bduni_srid(t.gcms_territoire)), 4326)) as geom

    FROM (
      -- decomposition liens_vers_route_nommee en lien_vers_route_nommee (split et duplication des lignes)
      SELECT * FROM {output_schema}.troncon_de_route UNION ALL SELECT * FROM {output_schema}.liaison_fictive_chor_frontaliere()
      -- SELECT t1.*, regexp_split_to_table( t1.liens_vers_route_nommee,'/') as lien_vers_route_nommee FROM troncon_de_route t1
    ) t
  ) s
    WHERE NOT detruit AND etat LIKE 'En service'
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
INSERT INTO {output_schema}.nodes (lon,lat,geom)
  SELECT ST_X(t.geom),ST_Y(t.geom),t.geom FROM t WHERE {output_schema}.nodes_id(t.geom) IS NULL
;

-- ############################
-- REMPLISSAGE DE edges
-- ############################

INSERT INTO {output_schema}.edges
  SELECT
    nextval('{output_schema}.edges_id_seq') AS id,
    {output_schema}.nodes_id(ST_StartPoint(geom)) as source_id,
    {output_schema}.nodes_id(ST_EndPoint(geom)) as target_id,
    ST_X(ST_StartPoint(geom)) as x1,
    ST_Y(ST_StartPoint(geom)) as y1,
    ST_X(ST_EndPoint(geom)) as x2,
    ST_Y(ST_EndPoint(geom)) as y2,
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
    importance as importance,
    CONCAT('{{"nom_1_gauche": "', nom_1_gauche, '", "nom_1_droite": "', nom_1_droite, '", "cpx_numero": "', cpx_numero, '", "cpx_toponyme": "', cpx_toponyme, '"}}') as way_names,
    nom_1_gauche as nom_1_gauche,
    nom_1_droite as nom_1_droite,
    cpx_numero as cpx_numero,
    cpx_toponyme as cpx_toponyme_route_nommee,
    sens_de_circulation as sens_de_circulation,
    position_par_rapport_au_sol as position_par_rapport_au_sol,
    acces_vehicule_leger as acces_vehicule_leger,
    largeur_de_chaussee as largeur_de_chaussee,
    nombre_de_voies as nombre_de_voies,
    insee_commune_gauche as insee_commune_gauche,
    insee_commune_droite as insee_commune_droite,
    bande_cyclable as bande_cyclable,
    itineraire_vert as itineraire_vert,
    reserve_aux_bus as reserve_aux_bus,
    urbain as urbain,
    acces_pieton as acces_pieton,
    nature_de_la_restriction as nature_de_la_restriction,
    restriction_de_hauteur as restriction_de_hauteur,
    restriction_de_poids_total as restriction_de_poids_total,
    restriction_de_poids_par_essieu as restriction_de_poids_par_essieu,
    restriction_de_largeur as restriction_de_largeur,
    restriction_de_longueur as restriction_de_longueur,
    matieres_dangereuses_interdites as matieres_dangereuses_interdites,
    cpx_gestionnaire as cpx_gestionnaire,
    cpx_numero_route_europeenne as cpx_numero_route_europeenne,
    cpx_classement_administratif as cpx_classement_administratif
  FROM bduni_troncon
;

-- ############################
-- REMPLISSAGE DE bduni_non_com
-- ############################

-- On ne conserve que les non communications sur la zone de calcul
DROP TABLE IF EXISTS {output_schema}.non_comm;
CREATE TABLE IF NOT EXISTS {output_schema}.non_comm AS
SELECT * FROM (
  SELECT
    cleabs,
    lien_vers_troncon_entree,
    -- liens_vers_troncon_sortie
    regexp_split_to_table(bduni_non_com_tmp.liens_vers_troncon_sortie, E'/') AS lien_vers_troncon_sortie
  FROM bduni_non_com_tmp
  WHERE lien_vers_troncon_entree IN (SELECT cleabs from {output_schema}.edges) AND NOT gcms_detruit
) AS non_comm_split
WHERE non_comm_split.lien_vers_troncon_sortie IN (SELECT cleabs from {output_schema}.edges);

-- Remplissage des ids d'edge dans la table des non communications
ALTER TABLE {output_schema}.non_comm ADD COLUMN IF NOT EXISTS id_from bigint;
ALTER TABLE {output_schema}.non_comm ADD COLUMN IF NOT EXISTS id_to bigint;

UPDATE {output_schema}.non_comm AS b SET id_from = e.id
FROM {output_schema}.edges as e
WHERE e.cleabs = b.lien_vers_troncon_entree
;

UPDATE {output_schema}.non_comm AS b SET id_to = e.id
FROM {output_schema}.edges as e
WHERE e.cleabs = b.lien_vers_troncon_sortie
;

-- Récupération du point commun entre deux troncons
CREATE OR REPLACE FUNCTION {output_schema}.common_point(id_from bigint, id_to bigint) RETURNS bigint AS $$
  SELECT
  CASE
    WHEN a.source_id=b.source_id THEN b.source_id
    WHEN a.source_id=b.target_id THEN b.target_id
    WHEN a.target_id=b.source_id THEN b.source_id
    WHEN a.target_id=b.target_id THEN b.target_id
    ELSE -1
  END
  FROM {output_schema}.edges as a, {output_schema}.edges as b
  WHERE a.id = id_from
  AND b.id = id_to;
$$ LANGUAGE SQL ;

ALTER TABLE {output_schema}.non_comm ADD COLUMN IF NOT EXISTS common_vertex_id bigint;
UPDATE {output_schema}.non_comm SET common_vertex_id = {output_schema}.common_point(non_comm.id_from, non_comm.id_to);

DROP FOREIGN TABLE IF EXISTS {output_schema}.troncon_de_route CASCADE;
DROP FOREIGN TABLE IF EXISTS {output_schema}.non_communication CASCADE;

END TRANSACTION;
VACUUM ANALYZE;
