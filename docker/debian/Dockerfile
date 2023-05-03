FROM python:3.10.9-slim-bullseye as build

### Installation des dépendances
RUN apt update && apt install -y wget git g++ cmake libboost-dev libboost-filesystem-dev libboost-thread-dev \
    libboost-system-dev libboost-regex-dev libxml2-dev libsparsehash-dev libbz2-dev \
    zlib1g-dev libzip-dev libgomp1 liblua5.3-dev \
    pkg-config libgdal-dev libboost-program-options-dev libboost-iostreams-dev \
    libboost-test-dev libtbb-dev libexpat1-dev

### Installation d'OSRM
WORKDIR /home/osrm/
RUN wget https://github.com/Project-OSRM/osrm-backend/archive/v5.26.0.tar.gz && tar -xzf v5.26.0.tar.gz && cd osrm-backend-5.26.0 && \
    mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && cmake --build . && cmake --build . --target package

### Installation de Valhalla
### Dépendances
RUN apt-get update && \
apt-get install -y cmake make libtool pkg-config g++ gcc curl unzip jq lcov protobuf-compiler \
vim-common locales libcurl4-openssl-dev zlib1g-dev liblz4-dev libprotobuf-dev && \
apt-get install -y libgeos-dev libgeos++-dev libluajit-5.1-dev libspatialite-dev libsqlite3-dev wget sqlite3 spatialite-bin python3-shapely && \
apt-get install -y libsqlite3-mod-spatialite

WORKDIR /home/prime-server
RUN apt-get install -y git cmake autoconf automake pkg-config libtool make gcc g++ lcov libcurl4-openssl-dev libzmq3-dev libczmq-dev
RUN git clone --depth 1 --recursive https://github.com/kevinkreiser/prime_server.git && cd prime_server && \
cmake -B build . && cmake --build build && make -C build install

WORKDIR /home/valhalla/
RUN pip install --upgrade "conan<2.0.0"
RUN git clone --branch 3.2.0-with_hard_exclude --depth 1 --recursive https://github.com/IGNF/valhalla.git && cd valhalla && \
mkdir build && cmake -B build -DCMAKE_BUILD_TYPE=Release && make -C build && make -C build package

FROM python:3.10.9-slim-bullseye as r2gg

ENV PYTHON_VERSION "3.10.9"
ENV HOME=/home

### Installation des dépendances pour OSRM
RUN apt update && apt install -y libboost-dev libboost-filesystem-dev libboost-thread-dev \
    libboost-system-dev libboost-regex-dev libxml2-dev libsparsehash-dev \
    libgomp1 liblua5.3-dev \
    pkg-config libgdal-dev libboost-program-options-dev libboost-iostreams-dev \
    libboost-test-dev libtbb-dev libexpat1-dev

### Installation des dépendances pour Valhalla
RUN apt-get update && \
    apt-get install -y libtool pkg-config curl unzip jq lcov protobuf-compiler \
    vim-common locales libcurl4-openssl-dev zlib1g-dev liblz4-dev libprotobuf-dev && \
    apt-get install -y libgeos-dev libgeos++-dev libluajit-5.1-dev libspatialite-dev libsqlite3-dev wget sqlite3 spatialite-bin python3-shapely && \
    apt-get install -y libsqlite3-mod-spatialite
RUN apt-get install -y git libcurl4-openssl-dev libzmq3-dev libczmq-dev

### Installation d'OSRM
COPY --from=build /home/osrm/osrm-backend-5.26.0/build/OSRM-0.1.1-Linux.tar.gz ./
RUN tar -xzvf OSRM-0.1.1-Linux.tar.gz && cd OSRM-0.1.1-Linux && cp -r bin/* /usr/bin/ && cp -r lib/* /usr/lib/ && cp -r include/* /usr/include/ && cp -r share/* /usr/share/

### Installation prime-server
COPY --from=build /usr/local/lib/libprime_server.so.0.7.0 /usr/lib/libprime_server.so.0.0.0
COPY --from=build /usr/local/lib/libprime_server.so.0 /usr/lib/libprime_server.so.0
COPY --from=build /usr/local/lib/libprime_server.so /usr/lib/libprime_server.so

### Installation de valhalla
COPY --from=build /home/valhalla/valhalla/build/valhalla-3.2.0-Linux.tar.gz ./
RUN tar -xzvf valhalla-3.2.0-Linux.tar.gz && cd valhalla-3.2.0-Linux && cp -r bin/* /usr/bin/ && cp -r lib/* /usr/lib/ && cp -r include/* /usr/include/ && cp -r share/* /usr/share/

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

