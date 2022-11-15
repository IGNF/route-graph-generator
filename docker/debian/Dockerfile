FROM python:3.6.13-slim-buster as osrm

### Installation des dépendances
RUN apt update && apt install -y wget git g++ cmake libboost-dev libboost-filesystem-dev libboost-thread-dev \
    libboost-system-dev libboost-regex-dev libxml2-dev libsparsehash-dev libbz2-dev \
    zlib1g-dev libzip-dev libgomp1 liblua5.3-dev \
    pkg-config libgdal-dev libboost-program-options-dev libboost-iostreams-dev \
    libboost-test-dev libtbb-dev libexpat1-dev

### Installation d'OSRM
WORKDIR /home/osrm/
RUN wget https://github.com/Project-OSRM/osrm-backend/archive/v5.25.0.tar.gz && tar -xzf v5.25.0.tar.gz && cd osrm-backend-5.25.0 && \
    mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && cmake --build . && cmake --build . --target package

FROM python:3.6.13-slim-buster as r2gg

ENV PYTHON_VERSION "3.6.13"
ENV HOME=/home

### Installation des dépendances pour OSRM
RUN apt update && apt install -y libboost-dev libboost-filesystem-dev libboost-thread-dev \
    libboost-system-dev libboost-regex-dev libxml2-dev libsparsehash-dev \
    libgomp1 liblua5.3-dev \
    pkg-config libgdal-dev libboost-program-options-dev libboost-iostreams-dev \
    libboost-test-dev libtbb-dev libexpat1-dev

### Installation d'OSRM
COPY --from=osrm /home/osrm/osrm-backend-5.25.0/build/OSRM-0.1.1-Linux.tar.gz ./
RUN tar -xzvf OSRM-0.1.1-Linux.tar.gz && cd OSRM-0.1.1-Linux && cp -r bin/* /usr/bin/ && cp -r lib/* /usr/lib/ && cp -r include/* /usr/include/ && cp -r share/* /usr/share/

### Installation de Valhalla
### Dépendances
RUN add-apt-repository -y ppa:valhalla-core/valhalla && apt-get update && \
apt-get install -y cmake make libtool pkg-config g++ gcc curl unzip jq lcov protobuf-compiler \
vim-common locales libcurl4-openssl-dev zlib1g-dev liblz4-dev libprime-server-dev libprotobuf-dev prime-server-bin && \
apt-get install -y libgeos-dev libgeos++-dev libluajit-5.1-dev libspatialite-dev libsqlite3-dev wget sqlite3 spatialite-bin python3-shapely && \
source /etc/lsb-release && apt-get install -y libsqlite3-mod-spatialite

WORKDIR /home/valhalla/
RUN git clone https://github.com/valhalla/valhalla.git && cd valhalla && git submodule update --init --recursive && \
mkdir build && cmake -B build -DCMAKE_BUILD_TYPE=Release && make -C build && make -C build install

### Installation des dépendances pour R2GG
#### Dépendances Python
RUN pip install 'psycopg2-binary==2.8.5' 'sqlparse==0.2.4' 'lxml==4.3.1' 'paramiko==2.7.2' 'scp==0.13.2'
### Installation de R2GG
WORKDIR /usr/lib/python3.6/site-packages/r2gg/r2gg
COPY r2gg ./
COPY setup.py ../
RUN cd ../ && pip install -e .

### Installation de wget pour l'image
RUN apt install wget

### Opérations pour le fonctionnement de l'image
#### Récupérations des scripts SQL du dépôt
WORKDIR /home/docker/sql
COPY sql/bduni_convert.sql ./bduni_convert.sql
#### Récupération des autres fichiers de configuration
WORKDIR /home/docker/config
COPY docker/config/* ./
#### Préparation d'un script bash pour lancer une génération complète
COPY docker/scripts/* ./
RUN ["chmod", "+x", "./r2gg_pipeline.sh"]
#### Montage d'un volume pour partager les données avec d'autres images
VOLUME ["/home/docker/data"]

