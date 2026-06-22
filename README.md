# Route Graph Generator

## Présentation

Route Graph Generator (r2gg) est un script Python qui permet la génération de graphes pour des moteurs de calcul d'itinéraire. Il a été développé pour générer les données directement utilisable par [Road2](https://github.com/IGNF/road2).

Actuellement, il y a trois formats de sortie : OSRM, pgRouting et Valhalla.

La conversion se fait via les fonctions de la bibliothèque r2gg développée dans ce but. Une documentation plus détaillée de r2gg est consultable [ici](https://ignf.github.io/route-graph-generator/).

## Génerer des données en local

Un docker compose est mis à disposition pour générer des données Valhalla en local.

```
UID=$(id -u) GID=$(id -g) docker compose up --build
```

Attendre l'import de la donnée, puis

```
docker compose exec r2gg sh -c "r2gg-sql2pivot docker/config/bdtopo2valhalla_local.json && r2gg-pivot2osm docker/config/bdtopo2valhalla_local.json && r2gg-osm2valhalla docker/config/bdtopo2valhalla_local.json && r2gg-road2config docker/config/bdtopo2valhalla_local.json"
```

Les données se trouveront dans le dossier ./data/generation

Pour faire tourner un service test valhalla sur les données ainsi générées, utiliser les commandes suivante:
```
docker run -dit valhalla -p 8002:8002 -v ${PWD}/data/generation:/custom_files -e use_tiles_ignore_pbf=True -e force_rebuild=False -e build_admins=False ghcr.io/valhalla/valhalla-scripted:latest
```

Puis checker la création d'itinéraire via le lien suivant
```
http://localhost:8002/route?json={"costing":"pedestrian","costing_options":{"pedestrian":{"use_ferry":0,"use_living_streets":0.5,"use_tracks":0,"private_access_penalty":450,"destination_only_penalty":300,"elevator_penalty":120,"service_penalty":15,"service_factor":1,"shortest":false,"type":"Foot","use_hills":0.5,"walking_speed":5.1,"walkway_factor":1,"sidewalk_factor":1,"alley_factor":2,"driveway_factor":5,"step_penalty":0,"max_hiking_difficulty":1,"use_lit":0,"transit_start_end_max_distance":2145,"transit_transfer_max_distance":800}},"exclude_polygons":[],"locations":[{"lon":2.320041,"lat":48.8588897,"type":"break"},{"lon":2.3380277,"lat":48.8611473,"type":"break"}],"units":"kilometers","alternates":2,"id":"valhalla_directions","language":"fr-FR","directions_options":{"format":"osrm"},"shape_format":"geojson","format":"osrm"}
```

## Prérequis

Les prérequis au fonctionnement des scripts de génération sont décrits dans le [readme](https://ignf.github.io/route-graph-generator/docker/readme.html) de l'image docker.

Les extensions SQL `postgres_fdw` et `PostGIS` doivent être installées sur la base de données `pivot` :

```sql
pivot=# CREATE EXTENSION postgres_fdw;
pivot=# CREATE EXTENSION PostGIS;
```

Dans le cas d'une convertion vers une base de données pgRouting, les extensions SQL `postgres_fdw`, `PostGIS` et `pgRouting` doivent être installées sur la base de données de destination, `pgrouting` par exemple :

```sql
pgrouting=# CREATE EXTENSION postgres_fdw;
pgrouting=# CREATE EXTENSION PostGIS;
pgrouting=# CREATE EXTENSION pgRouting;
```

Les procédures du projet [pgrouting-procedures](https://github.com/IGNF/pgrouting-procedures) doivent également être installées sur la base de données de destination, sur le bon schema


## Installation

Pour installer les commandes de génération de données, lancer la commande suivante à la racine du projet :

```
pip3 install --user -e .
```

## Utilisation

### Fichier de configuration

Pour pouvoir lancer les scripts de génération, il faut définir une configuration (au format JSON) par ressource à générer. Ce fichier de configuration fait références à d'autres fichiers de configuration : pour la gestion des logs, la gestion des connexions aux bases de données, et pour le calcul des coûts.
Des exemples de tous ces fichiers sont présents dans le dépôt dans le dossier `io`.
La documentation de ces fichiers de configuration est consultable [ici](https://github.com/IGNF/route-graph-generator/tree/master/io).

Un exemple de ces fichiers est disponible dans la partie [docker](https://github.com/IGNF/route-graph-generator/tree/master/docker/config).

### Exécution

Les scripts de génération sont divisés en trois processus distincts : l'extraction des données d'une base de données vers une base de données dite "pivot", et, en fonction de la ressource, la conversion depuis la base "pivot" vers une base pgRouting, ou vers des fichiers `.osrm`, ou encore vers des fichiers `valhalla`.

Ces trois processus se lancent à l'aide de commandes différentes, prenant toutes le même fichier de configuration.

Pour extraire les données vers la base pivot

```
r2gg-sql2pivot config.json
```

Pour convertir les données au fromat pgRouting (le type de ressource dans config.json doit être `pgr`)

```
r2gg-pivot2pgrouting config.json
```

Pour convertir les données au format osrm (le type de ressource dans config.json doit être `osrm`)

```
r2gg-pivot2osm config.json
r2gg-osm2osrm config.json
```

Pour convertir les données au format valhalla (le type de ressource dans config.json doit être `valhalla`)

```
r2gg-pivot2osm config.json
r2gg-osm2valhalla config.json
```

Enfin, si on souhaite générer la configuration pour Road2, il y a une dernière commande

```
r2gg-road2config config.json
```

## Version

Elle est indiquée dans le `__about__.py`.

## Licence

Route-graph-generator est diffusé sous la licence GPL v3.

## Participer aux développements

Les participations à ce projet sont encouragées (votre notre [charte](./CODE_OF_CONDUCT.md) à ce sujet). Nous avons mis en place un [guide](./CONTRIBUTING.md) des contributions pour vous accompagner dans cette démarche.
