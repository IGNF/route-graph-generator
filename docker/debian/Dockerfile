# OSRM binaries
FROM ghcr.io/project-osrm/osrm-backend:26.4-debian AS osrm

# Final runtime image
FROM python:3.12-slim-trixie AS r2gg

ENV PYTHON_VERSION="3.12"
ENV HOME=/home

COPY --from=osrm /usr/local/bin/osrm-* /usr/local/bin/
COPY --from=osrm /usr/local/lib /usr/local/lib
COPY --from=osrm /usr/lib/x86_64-linux-gnu/libboost_* /usr/lib/x86_64-linux-gnu/
COPY --from=osrm /usr/lib/x86_64-linux-gnu/liblua* /usr/lib/x86_64-linux-gnu/
COPY --from=osrm /usr/lib/x86_64-linux-gnu/libexpat* /usr/lib/x86_64-linux-gnu/
COPY --from=osrm /usr/lib/x86_64-linux-gnu/libtbb* /usr/lib/x86_64-linux-gnu/

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

