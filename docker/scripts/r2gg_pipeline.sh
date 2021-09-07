#!/usr/bin/env sh


# ## S'il n'y a rien, on fait une génération à partir de données OSM sur la Corse en utilisant un fichier de configuration déjà présent dans l'image docker
# if [ $R2GG_GENERATION_CONF = "" ]; then
  
# ## S'il y a une configuration, alors on donne cette configuration à r2gg qui se chargera de l'analyser et d'agir en conséquence 
# else

# fi

# # On lance la génération 
r2gg:populate_pivot $R2GG_ARG

if [ $GENERATION_TYPE = "osrm" ]; then
  r2gg:pivot2osrm $R2GG_ARG
elif [ $GENERATION_TYPE = "pgr" ]; then
  r2gg:pivot2pgrouting $R2GG_ARG
fi
