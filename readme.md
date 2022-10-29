# Route Graph Generator

Scripts de génération de graphes permettant des calculs d'itinéraires.
Il y a deux formats de sortie : OSRM et pgRouting

La conversion se fait via les fonctions de la bibliothèque r2gg développée dans ce but. Une documentation plus détaillée de r2gg est consultable [ici](r2gg).

## Prérequis
Les prérequis au fonctionnement des scipts de génération sont décrits dans le [readme](docker) de l'image docker.

## Installation
Pour installer les commandes de génération de données, lancer la commande suivante à la racine du projet :
```
pip3 install --user -e .
```

## Utilisation

### Fichier de configuration
Pour pouvoir lancer les scripts de génération, il faut définir une configuration (au format JSON) par ressource à générer. Ce fichier de configuration fait références à d'autres fichiers de configuration : pour la gestion des logs, la gestion des connexions aux bases de données, et pour le calcul des coûts.
Des exemples de tous ces fichiers sont présents dans le dépôt dans le dossier `io`.
La documentation de ces fichiers de configuration est consultable [ici](io).

### Exécution
Les scripts de génération sont divisés en trois processus distincts : l'extraction des données d'une base de données vers un base de données dite "pivot", et, en fonction de la ressource, la conversion depuis la base "pivot" vers une base pgRouting, ou vers des fichiers `.osrm`.
Ces trois processus se lancent à l'aide de trois commandes différentes, prenant toutes le même fichier de configuration.

Pour extraire les données vers la base pivot
```
r2gg-populate_pivot config.json
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
## Version

Version du code 1.1.0

NB: penser à mettre à jour la version dans le script `__init__.py` et dans le `setup.py`

## Licence

Route-graph-generator est diffusé sous la licence GPL v3.
