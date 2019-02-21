# Route Graph Generator

Scripts de génération de graphes permettant des calculs d'itinéraires.
Il y a deux formats de sortie : OSRM et pgRouting

La conversion se fait via les fonctions de la bibliothèque r2gg développée dans ce but.


## Prérequis :
Cf. Dockerfile

## Installation :
À la source du projet :
```
pip3 install --user -e .
```

## Utilisation :
Pour extraire les données vers la base pivot
```
r2gg:populate_pivot config.json
```
Pour convertir les données au fromat pgRouting (le trype de ressource dans config.json doit être pgr)
```
r2gg:pivot2pgrouting config.json
```
```
r2gg:pivot2osrm config.json
```
