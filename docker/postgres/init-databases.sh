#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    SELECT 'CREATE DATABASE ${EVOLUTION_DB:-evolution}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${EVOLUTION_DB:-evolution}')\gexec
EOSQL
