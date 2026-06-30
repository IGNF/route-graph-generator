FROM debian:12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    gdal-bin \
    p7zip-full \
    wget \
    ca-certificates \
    postgresql-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /import
COPY import_gpkg.sh /import/import_gpkg.sh
RUN chmod +x /import/import_gpkg.sh

ENTRYPOINT ["/import/import_gpkg.sh"]