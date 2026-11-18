#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Uso: $0 <caminho-do-backup.tar.gz>" >&2
    exit 1
fi

ARCHIVE_PATH="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "Arquivo de backup não encontrado: $ARCHIVE_PATH" >&2
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

PG_USER="${POSTGRES_USER:-infinity}"
PG_DB="${POSTGRES_DB:-infinity_api}"
EVO_DB="${EVOLUTION_DB:-evolution}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[restore.sh] Extraindo ${ARCHIVE_PATH}..."
tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"

echo "[restore.sh] Parando serviços dependentes (api, evolution-api, redis)..."
docker compose stop api evolution-api redis

echo "[restore.sh] Garantindo PostgreSQL ativo..."
docker compose up -d postgres
until docker compose exec -T postgres pg_isready -U "$PG_USER" >/dev/null 2>&1; do
    sleep 2
done

if [ -f "${TMP_DIR}/infinity_api.sql.gz" ]; then
    echo "[restore.sh] Restaurando banco ${PG_DB}..."
    docker compose exec -T postgres psql -U "$PG_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PG_DB}' AND pid <> pg_backend_pid();" >/dev/null
    docker compose exec -T postgres dropdb -U "$PG_USER" --if-exists "$PG_DB"
    docker compose exec -T postgres createdb -U "$PG_USER" "$PG_DB"
    gunzip -c "${TMP_DIR}/infinity_api.sql.gz" | docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" >/dev/null
fi

if [ -f "${TMP_DIR}/evolution.sql.gz" ]; then
    echo "[restore.sh] Restaurando banco ${EVO_DB}..."
    docker compose exec -T postgres psql -U "$PG_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${EVO_DB}' AND pid <> pg_backend_pid();" >/dev/null
    docker compose exec -T postgres dropdb -U "$PG_USER" --if-exists "$EVO_DB"
    docker compose exec -T postgres createdb -U "$PG_USER" "$EVO_DB"
    gunzip -c "${TMP_DIR}/evolution.sql.gz" | docker compose exec -T postgres psql -U "$PG_USER" -d "$EVO_DB" >/dev/null
fi

if [ -f "${TMP_DIR}/evolution_instances.tar.gz" ]; then
    echo "[restore.sh] Restaurando volume infinity_evolution_instances..."
    docker run --rm \
        -v infinity_evolution_instances:/dest \
        -v "${TMP_DIR}:/src:ro" \
        alpine:3.20 sh -c "rm -rf /dest/* && tar -xzf /src/evolution_instances.tar.gz -C /dest"
fi

if [ -f "${TMP_DIR}/redis_data.tar.gz" ]; then
    echo "[restore.sh] Restaurando volume infinity_redis_data..."
    docker run --rm \
        -v infinity_redis_data:/dest \
        -v "${TMP_DIR}:/src:ro" \
        alpine:3.20 sh -c "rm -rf /dest/* && tar -xzf /src/redis_data.tar.gz -C /dest"
fi

echo "[restore.sh] Subindo todos os serviços..."
docker compose up -d

echo "[restore.sh] Restauração concluída com sucesso!"
