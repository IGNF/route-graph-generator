#!/usr/bin/env sh


## S'il n'y a rien, on fait une génération à partir de données OSM sur la Corse en utilisant un fichier de configuration déjà présent dans l'image docker
if [ ! $R2GG_ARG ]
then

  mkdir -v /home/docker/data/data-osm-latest
  cd /home/docker/data/data-osm-latest
  wget -O data-osm-latest.osm.pbf download.geofabrik.de/europe/france/corse-latest.osm.pbf
  osrm-extract data-osm-latest.osm.pbf -p /usr/share/osrm/profiles/car.lua
  osrm-contract data-osm-latest.osrm
  cp -v /home/docker/config/data-osm.resource /home/docker/data/resources/
  cp -v /home/docker/config/data-osm.source /home/docker/data/sources/

## S'il y a une configuration, alors on donne cette configuration à r2gg qui se chargera de l'analyser et d'agir en conséquence
else

  # On lance une génération à partir du fichier de configuration
  r2gg-sql2pivot $R2GG_ARG

  if [ $GENERATION_TYPE = "osrm" ]
  then
    r2gg-pivot2osm $R2GG_ARG
    r2gg-osm2osrm $R2GG_ARG
  elif [ $GENERATION_TYPE = "pgr" ]
  then
    r2gg-pivot2pgrouting $R2GG_ARG
  elif [ $GENERATION_TYPE = "valhalla" ]
  then
    r2gg-pivot2osm $R2GG_ARG
    r2gg-osm2valhalla $R2GG_ARG
  fi

  r2gg-road2config $R2GG_ARG

fi


