#!/usr/bin/env bash
set -euo pipefail

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
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

TS="$(date -u +"%Y%m%d_%H%M%S")"
BACKUP_ROOT="${ROOT_DIR}/backups"
STAGE_DIR="${BACKUP_ROOT}/manual_${TS}"
ARCHIVE="${BACKUP_ROOT}/manual_backup_${TS}.tar.gz"

mkdir -p "$STAGE_DIR"
trap 'rm -rf "$STAGE_DIR"' EXIT

echo "[backup.sh] Salvando snapshot do Redis..."
docker compose exec -T redis redis-cli save >/dev/null

echo "[backup.sh] Exportando PostgreSQL (${PG_DB} e ${EVO_DB})..."
docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" | gzip > "${STAGE_DIR}/infinity_api.sql.gz"
docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$EVO_DB" | gzip > "${STAGE_DIR}/evolution.sql.gz"

echo "[backup.sh] Exportando volume infinity_evolution_instances..."
docker run --rm \
    -v infinity_evolution_instances:/source:ro \
    -v "${STAGE_DIR}:/dest" \
    alpine:3.20 tar -czf /dest/evolution_instances.tar.gz -C /source .

echo "[backup.sh] Exportando volume infinity_redis_data..."
docker run --rm \
    -v infinity_redis_data:/source:ro \
    -v "${STAGE_DIR}:/dest" \
    alpine:3.20 tar -czf /dest/redis_data.tar.gz -C /source .

tar -czf "$ARCHIVE" -C "$STAGE_DIR" .
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"

find "$BACKUP_ROOT" -maxdepth 1 -type f \
    \( -name "manual_backup_*.tar.gz*" -o -name "full_backup_*.tar.gz*" -o -name "snapshot_*.json.gz" \) \
    -mtime +"$RETENTION_DAYS" -delete

echo "[backup.sh] Backup manual criado com sucesso: ${ARCHIVE}"
