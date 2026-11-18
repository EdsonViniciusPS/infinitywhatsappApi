#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATE_SCRIPT="${ROOT_DIR}/scripts/update-vps.sh"
LOG_FILE="/var/log/infinity-auto-update.log"
CRON_EXPR="0 4 */7 * * ${UPDATE_SCRIPT} >> ${LOG_FILE} 2>&1"
CRON_TAG="# infinity-whatsapp-auto-update"

chmod +x "${ROOT_DIR}/scripts/"*.sh "${ROOT_DIR}/docker/backup/entrypoint.sh" "${ROOT_DIR}/docker/postgres/init-databases.sh"

CURRENT_CRON="$(crontab -l 2>/dev/null || true)"
FILTERED_CRON="$(printf "%s\n" "$CURRENT_CRON" | grep -v "$CRON_TAG" | grep -v "$UPDATE_SCRIPT" || true)"

{
    printf "%s\n" "$FILTERED_CRON"
    printf "%s %s\n" "$CRON_EXPR" "$CRON_TAG"
} | sed '/^$/N;/^\n$/D' | crontab -

echo "[setup-auto-update] Cron configurado para atualizar e limpar memória a cada 7 dias (04:00):"
echo "  ${CRON_EXPR}"
