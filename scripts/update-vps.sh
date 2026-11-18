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
LOG_DAYS="${LOG_RETENTION_DAYS:-7}"

echo "[update-vps] 1/7 Gerando backup preventivo antes da atualização..."
./scripts/backup.sh

echo "[update-vps] 2/7 Atualizando repositório e imagens base..."
git pull --ff-only
docker compose pull --ignore-buildable

echo "[update-vps] 3/7 Reconstruindo e reiniciando containers (preservando volumes e renovando RAM)..."
docker compose up -d --build --remove-orphans

echo "[update-vps] 4/7 Aplicando migrations pendentes do Alembic..."
docker compose exec -T api alembic upgrade head

echo "[update-vps] 5/7 Limpando logs antigos (>${LOG_DAYS} dias) e executando VACUUM ANALYZE..."
docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 <<-EOSQL
    DELETE FROM message_logs WHERE created_at < NOW() - INTERVAL '${LOG_DAYS} days';
    DELETE FROM webhook_deliveries WHERE created_at < NOW() - INTERVAL '${LOG_DAYS} days';
    VACUUM ANALYZE;
EOSQL
docker compose exec -T postgres psql -U "$PG_USER" -d "$EVO_DB" -c "VACUUM ANALYZE;" >/dev/null

echo "[update-vps] 6/7 Removendo imagens e caches antigos do Docker (sem remover volumes)..."
docker image prune -af
docker builder prune -af

echo "[update-vps] 7/7 Validando healthcheck da API..."
for i in $(seq 1 15); do
    if docker compose exec -T api curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        echo "[update-vps] Atualização semanal concluída com sucesso e API saudável!"
        exit 0
    fi
    sleep 2
done

echo "[update-vps] AVISO: API não respondeu ao healthcheck a tempo." >&2
exit 1
