#!/usr/bin/env bash
set -euo pipefail

# Environment variables expected:
# PGHOST, PGPORT, PGUSER, PGPASSWORD, SOURCE_DB, GPKG_URL, GPKG_IN_ARCHIVE

: "${PGHOST:=db}"
: "${PGPORT:=5432}"
: "${PGUSER:=r2gg}"
: "${PGPASSWORD:=r2gg}"
: "${SOURCE_DB:=source_db}"
: "${GPKG_URL:?Please set GPKG_URL}"
: "${GPKG_IN_ARCHIVE:?Please set GPKG_IN_ARCHIVE}"

TMPDIR=/tmp/gpkg_import
mkdir -p "$TMPDIR"
cd "$TMPDIR"

echo "Waiting for database at ${PGHOST}:${PGPORT}..."
until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" >/dev/null 2>&1; do
  sleep 1
done
echo "Database ready."

export PGPASSWORD="$PGPASSWORD"

echo "Creating database ${SOURCE_DB} (if not exists)"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "CREATE DATABASE ${SOURCE_DB};" || true
echo "Ensuring PostGIS extension in ${SOURCE_DB}"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$SOURCE_DB" -c "CREATE EXTENSION IF NOT EXISTS postgis;" || true

echo "Downloading ${GPKG_URL}..."
wget -O archive.7z "$GPKG_URL"

echo "Extracting ${GPKG_IN_ARCHIVE}..."
7z x archive.7z "$GPKG_IN_ARCHIVE" -oextracted -y >/dev/null
GPKG_PATH="extracted/${GPKG_IN_ARCHIVE}"
if [ ! -f "$GPKG_PATH" ]; then
  echo "Expected gpkg at $GPKG_PATH not found; listing extracted files:"
  find extracted -maxdepth 5 -type f -print
  exit 1
fi

echo "Importing $GPKG_PATH into database ${SOURCE_DB}..."
ogr2ogr -f "PostgreSQL" \
  PG:"host=${PGHOST} user=${PGUSER} dbname=${SOURCE_DB} password=${PGPASSWORD} port=${PGPORT}" \
  "$GPKG_PATH" -overwrite -progress

echo "Import completed."
