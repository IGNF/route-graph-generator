# OSRM binaries
FROM ghcr.io/project-osrm/osrm-backend:v6.0.0 AS osrm

# Valhalla binaries
FROM ghcr.io/valhalla/valhalla:3.6.1 AS valhalla

# Prime server build
FROM debian:bookworm AS prime_build
RUN apt-get update && apt-get install -y \
    git cmake make gcc g++ pkg-config \
    libcurl4-openssl-dev libzmq3-dev libczmq-dev

RUN git clone --depth 1 --recursive https://github.com/kevinkreiser/prime_server.git
WORKDIR /prime_server
RUN cmake -B build . && cmake --build build && make -C build install

# Final runtime image
FROM python:3.10.19-slim-trixie AS r2gg

ENV PYTHON_VERSION="3.10.9"
ENV HOME=/home

# Runtime dependencies only
RUN apt-get update && apt-get install -y \
    libboost-filesystem-dev libboost-system-dev \
    libcurl4 libprotobuf-dev libgeos-dev \
    libluajit-5.1-2 libsqlite3-mod-spatialite \
    && rm -rf /var/lib/apt/lists/*

COPY --from=osrm /usr/local/bin/osrm-* /usr/local/bin/
COPY --from=osrm /usr/local/lib /usr/local/lib

### Installation prime-server
COPY --from=prime_build /usr/local/lib/libprime_server.so* /usr/lib/

### Installation de valhalla
COPY --from=valhalla /usr/local/bin/valhalla_* /usr/local/bin/
COPY --from=valhalla /usr/local/lib/libvalhalla* /usr/local/lib/

### Installation des dépendances pour psycopg2
RUN apt update && \
    apt install -y libpq-dev gcc
#### Dépendances Python
### Installation de R2GG
WORKDIR /user/app

COPY requirements.txt ./
COPY requirements/base.txt ./requirements/

RUN python -m pip install --no-cache-dir -U pip && \
    python -m pip install --no-cache-dir -U setuptools wheel

COPY . ./

RUN python -m pip install -U --no-cache-dir -r requirements.txt

RUN python -m pip install -e .

### Installation de wget pour l'image
RUN apt-get install -y wget

### Opérations pour le fonctionnement de l'image
#### Récupérations des scripts SQL du dépôt
WORKDIR /home/docker/sql
COPY sql/*.sql ./
#### Récupération des autres fichiers de configuration
WORKDIR /home/docker/config
COPY docker/config/* ./
#### Préparation d'un script bash pour lancer une génération complète
COPY docker/scripts/* ./
RUN ["chmod", "+x", "./r2gg_pipeline.sh"]
#### Montage d'un volume pour partager les données avec d'autres images
VOLUME ["/home/docker/data"]

