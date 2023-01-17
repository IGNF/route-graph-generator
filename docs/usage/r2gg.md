# r2gg : road2 graph generator

Bibliothèque de scripts Python permettant la génération de graphs utilisables par l'application road2

## Fonctions publiques

Les fonctions publiques exposées par r2gg permettent de réaliser les trois processus des scripts de génération. Les fonctions utile à une génération complète peuvent être lancées via la commande suivante :
`python3 r2gg.fonction config.json`

Au passage, ces fonctions ont toutes besoin d'un fichier de configuration (décrit [ici](./configuration.md)) pour pouvoir fonctionner. Des exemples sont disponibles dans le dossier [`docker/config`](../../docker/config/).

Mais on peut décider de n'en lancer que certaines selon le résultat que l'on souhaite obtenir. 

### `sql2pivot()`
Cette fonction permet d'extraire des données SQL d'un format quelconque vers la base pivot dans le format pivot. 

### `pivot2pgrouting()`
Permet de convertir les données au fromat pgRouting (le type de ressource dans config.json doit être `pgr`).

### `pivot2osm()`
Permet de convertir les données au fromat osm. Le type de ressource dans config.json doit être `osrm` ou `valhalla`, sachant que le premier donnera des `.osm` et le second des `.osm.pbf`. 

### `osm2osrm()`
Permet de convertir des données OSM en données OSRM. 

### `osm2valhalla()`
Permet de convertir des données OSM (`.osm` ou `.osm.pbf`) en données Valhalla. 

### `road2config()`
Permet de générer la configuration utile à Road2 pour lire les données. 

## Fonctions privées

Chacune des fonctions publiques est en fait l'enchaînement de deux fonctions privées :

- `_configure()` qui lit le fichier de configuration fourni en argument et initialise la connexion à la base de donnée pivot. Cette fonction est définie dans le fichier `_configure.py`
- Une fonction permettant la conversion à proprement parler. Ces fonctions sont définies dans le fichier `_main.py`

### Liste des fichiers

- `__init__.py` expose les fonctions publiques
- `_configure.py` contient la fonction qui permet la configuration du script à l'aide du fichier de configuration
- `_file_copier.py` permet de copier un fichier
- `_lua_builder.py` permet de construire les LUA pour OSRM
- `_main.py` contient les fonctions de conversion et de génération des données à partir de la configuration
- `_osm_building.py` contient les fonctions permettant la construction de fichier osm
- `_osm_to_pbf.py` permet de convertir un `.osm` avec `.osm.pbf`
- `_output_costs_from_costs_config.py` contient la fonction permettant de calculer des coûts à partir d'un fichier de configuration des coûts
- `_path_converter.py` permet de convertir un chemin de fichier pour un autre dossier
- `_pivot_to_osm.py` permet la conversion des données au format pivot vers un fichier `.osm`
- `_pivot_to_pgr.py` permet la conversion des données au format pivot vers une base pgrouting
- `_read_config.py` permet la lecture des fichiers de configuration au format JSON
- `_sql_building.py` contient des fonctions pour construire des requêtes SQL
- `_subprocess_execution.py` permet l'exécution de lignes de commandes par les scripts
- `_valhalla_lua_builder.py` permet de construire le LUA pour valhalla
