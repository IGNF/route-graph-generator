#!/usr/bin/env sh

# TODO : On analyse certaines VARENV 
## S'il n'y a rien, on fait une génération à partir de données OSM sur la Corse

## S'il y a un nom de donnée OSM, on fait cette génération

## S'il y a un fichier de configuration, on lance avec ce fichier


# On lance la génération 
r2gg:populate_pivot $R2GG_ARG

if [ $GENERATION_TYPE = "osrm" ]; then
  r2gg:pivot2osrm $R2GG_ARG
elif [ $GENERATION_TYPE = "pgr" ]; then
  r2gg:pivot2pgrouting $R2GG_ARG
fi
