# r2gg : road2 graph generator
Bibliothèque de scripts Python permettant la génération de graphs utilisables par l'application road2

## Fonctions publiques
Les fonctions publiques exposées par r2gg permettent de réaliser les trois processus des scripts de génération. Ces fonctions doivent être lancées via la commande suivante :
`python3 r2gg.fonction config.json`
Elles ont en effet besoin d'un fichier de configuration (décrit [ici](../io)) pour pouvoir fonctionner.

### `sql2pivot()`
Cette fonction permet d'extraire des données SQL d'un format quelconque vers la base pivot dans le format pivot

### `pivot2pgrouting()`
Permet de convertir les données au fromat pgRouting (le type de ressource dans config.json doit être `pgr`)

### `pivot2osrm()`
Permet de convertir les données au fromat osrm (le type de ressource dans config.json doit être `osrm`)


## Fonctions privées
Chacune des fonctions publiques est en fait l'enchaînement de deux fonctions privées :
- `_configure()` qui lit le fichier de configuration fourni en argument et initialise la connexion à la base de donnée pivot. Cette fonction est définie dans le fichier `_configure.py`
- Une fonction permettant la conversion à proprement parler. Ces fonctions sont définies dans le fichier `_main.py`

### Liste des fichiers
- `_configure.py` contient la fonction qui permet la configuration du script à l'aide du fichier de configuration
- `__init__.py` expose les fonctions publiques
- `_main.py` contient les fonctions de conversion et de génération des données à partir de la configuration
- `_osm_building.py` contient les fonctions permettant la construction de fichier osm
- `_output_costs_from_costs_config.py` contient la fonction permettant de calculer des coûts à partir d'un fichier de configuration des coûts
- `_pivot_to_osm.py` permet la conversion des données au format pivot vers un fichier `.osm`
- `_pivot_to_pgr.py` permet la conversion des données au format pivot vers une base pgrouting
- `_read_config.py` permet la lecture des fichiers de configuration au format JSON
- `_sql_building.py` contient des fonctions pour construire des requêtes SQL
- `_subprocess_execution.py` permet l'exécution de lignes de commandes par les scripts
