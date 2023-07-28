-- Usefull functions 
CREATE OR REPLACE FUNCTION nodes_id( _geom geometry ) RETURNS bigint AS $$
  SELECT id FROM nodes WHERE lon = ST_X(_geom) AND lat = ST_Y(_geom);
$$ LANGUAGE SQL ;

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

-- Create the nodes table 
CREATE TABLE IF NOT EXISTS nodes (
  id bigserial primary key,
  lon double precision,
  lat double precision,
  geom geometry(Point,4326)
);
-- Create indexes on nodes
CREATE INDEX IF NOT EXISTS nodes_geom_gist ON nodes USING GIST (geom);
CREATE INDEX IF NOT EXISTS nodes_lon_lat_idx ON nodes(lon,lat);

-- Modify edges table to match to the pivot
ALTER TABLE edges rename way_id TO id;

-- Add indexes on edges
CREATE INDEX geom_way_idx on edges using GIST(geom);
CREATE INDEX id_way_idx on edges (id);

-- Fill nodes 
WITH t AS (
  SELECT ST_Force2D(ST_StartPoint(geom)) as geom FROM edges
    UNION
  SELECT ST_Force2D(ST_EndPoint(geom)) as geom FROM edges
)
INSERT INTO nodes (lon,lat,geom)
  SELECT ST_X(t.geom),ST_Y(t.geom),t.geom FROM t WHERE nodes_id(t.geom) IS NULL
;

-- Fill empty columns inside edges 
UPDATE edges SET length_m = ST_length(geography(ST_Transform(geom, 4326)));

UPDATE edges SET source_id = nodes_id(ST_StartPoint(geom));
UPDATE edges SET target_id = nodes_id(ST_EndPoint(geom));

-- Fill empty columns inside non_comm
UPDATE non_comm SET common_vertex_id = common_point(non_comm.id_from, non_comm.id_to);
