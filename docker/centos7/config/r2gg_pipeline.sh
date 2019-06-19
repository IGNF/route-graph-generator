#!/usr/bin/env sh

r2gg:populate_pivot $R2GG_ARG

if [ $GENERATION_TYPE = "osrm" ]; then
  r2gg:pivot2osrm $R2GG_ARG
elif [ $GENERATION_TYPE = "pgr" ]; then
  r2gg:pivot2pgrouting $R2GG_ARG
fi
