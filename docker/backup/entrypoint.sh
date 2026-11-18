#!/bin/sh
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-21600}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
PG_USER="${POSTGRES_USER:-infinity}"
PG_DB="${POSTGRES_DB:-infinity_api}"
EVO_DB="${EVOLUTION_DB:-evolution}"

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

stop_requested=0
trap 'stop_requested=1' TERM INT

run_backup() {
    TS="$(date -u +"%Y%m%d_%H%M%S")"
    STAGE_DIR="/backups/auto_${TS}"
    ARCHIVE="/backups/full_backup_${TS}.tar.gz"

    mkdir -p "$STAGE_DIR"

    echo "[backup] (${TS}) Aguardando PostgreSQL ficar pronto..."
    until pg_isready -h postgres -U "$PG_USER" >/dev/null 2>&1; do
        sleep 2
    done

    echo "[backup] (${TS}) Gerando dump de ${PG_DB}..."
    pg_dump -h postgres -U "$PG_USER" -d "$PG_DB" | gzip > "${STAGE_DIR}/infinity_api.sql.gz"

    echo "[backup] (${TS}) Gerando dump de ${EVO_DB}..."
    pg_dump -h postgres -U "$PG_USER" -d "$EVO_DB" | gzip > "${STAGE_DIR}/evolution.sql.gz"

    echo "[backup] (${TS}) Compactando instâncias da Evolution API..."
    tar -czf "${STAGE_DIR}/evolution_instances.tar.gz" -C /evolution/instances .

    echo "[backup] (${TS}) Compactando dados persistentes do Redis..."
    tar -czf "${STAGE_DIR}/redis_data.tar.gz" -C /redis-data .

    tar -czf "$ARCHIVE" -C "$STAGE_DIR" .
    sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"
    rm -rf "$STAGE_DIR"

    echo "[backup] (${TS}) Backup concluído: ${ARCHIVE}"

    find /backups -maxdepth 1 -type f \
        \( -name "full_backup_*.tar.gz" -o -name "full_backup_*.tar.gz.sha256" -o -name "manual_backup_*.tar.gz*" -o -name "snapshot_*.json.gz" \) \
        -mtime +"$RETENTION_DAYS" -delete
}

while [ "$stop_requested" -eq 0 ]; do
    if ! run_backup; then
        echo "[backup] ERRO ao executar backup automático." >&2
    fi

    slept=0
    while [ "$slept" -lt "$INTERVAL" ] && [ "$stop_requested" -eq 0 ]; do
        sleep 5
        slept=$((slept + 5))
    done
done

echo "[backup] Encerrando sidecar de backup com segurança."
