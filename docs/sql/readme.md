# Scripts SQL

Les scripts SQL doivent permettre la conversion d'une base de données sources vers un format pivot.
Les spécifications de ce dernier sont les suivantes :

## Table "nodes"

```sql
CREATE TABLE IF NOT EXISTS nodes (
  id bigserial primary key,
  lon double precision,
  lat double precision,
  geom geometry(Point,4326)
  -- Éventuels attributs facultatifs, définis en focntion des données en entrée
);
```

## Table "edges"

```sql
CREATE TABLE IF NOT EXISTS edges (
  id bigserial primary key,
  source_id bigserial,
  target_id bigserial,
  length_m double precision,
  direction integer,
  geom geometry(Linestring,4326),
  -- Attributs facultatifs, ici pour l'exemple des attributs de la bduni
  -- Attributs spécifiques à la bd uni
  vitesse_moyenne_vl integer,
  nature text,
  cleabs text
);
```
