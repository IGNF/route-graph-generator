#!/usr/bin/env sh

echo "debut"
date +%Y-%m-%dT%H:%M:%S
r2gg-pivot2osm /home/docker/config/bdtopo2osrm.json
echo "fin pivot2osm"
date +%Y-%m-%dT%H:%M:%S
r2gg-osm2osrm /home/docker/config/bdtopo2osrm.json
echo "fin"
date +%Y-%m-%dT%H:%M:%S
