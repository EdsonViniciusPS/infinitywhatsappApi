#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

generate_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import secrets; print(secrets.token_hex(32))"
    else
        head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
    fi
}

get_env_value() {
    local key="$1"
    grep -E "^${key}=" .env | tail -n 1 | cut -d'=' -f2- | sed -e 's/^"//' -e 's/"$//'
}

set_env_value() {
    local key="$1"
    local value="$2"
    if grep -qE "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${value}|" .env
    else
        printf "%s=%s\n" "$key" "$value" >> .env
    fi
}

echo "[deploy-vps] 1/6 Verificando arquivo .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[deploy-vps] Arquivo .env criado a partir de .env.example."
fi

for secret_key in JWT_SECRET_KEY ADMIN_MASTER_KEY EVOLUTION_WEBHOOK_SECRET EVOLUTION_API_KEY; do
    current_val="$(get_env_value "$secret_key")"
    if [ -z "$current_val" ] || [[ "$current_val" == change-me-* ]]; then
        set_env_value "$secret_key" "$(generate_secret)"
        echo "[deploy-vps] Segredo gerado para ${secret_key}."
    fi
done

pg_user="$(get_env_value POSTGRES_USER)"
pg_user="${pg_user:-infinity}"
pg_db="$(get_env_value POSTGRES_DB)"
pg_db="${pg_db:-infinity_api}"
pg_pass="$(get_env_value POSTGRES_PASSWORD)"
if [ -z "$pg_pass" ] || [[ "$pg_pass" == change-me-* ]]; then
    pg_pass="$(generate_secret)"
    set_env_value "POSTGRES_PASSWORD" "$pg_pass"
    set_env_value "DATABASE_URL" "postgresql+asyncpg://${pg_user}:${pg_pass}@postgres:5432/${pg_db}"
    echo "[deploy-vps] Senha forte gerada para POSTGRES_PASSWORD e sincronizada em DATABASE_URL."
else
    db_url="$(get_env_value DATABASE_URL)"
    if [[ "$db_url" == *change-me-db-password* ]]; then
        set_env_value "DATABASE_URL" "postgresql+asyncpg://${pg_user}:${pg_pass}@postgres:5432/${pg_db}"
        echo "[deploy-vps] DATABASE_URL sincronizada com POSTGRES_PASSWORD."
    fi
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

echo "[deploy-vps] 2/6 Garantindo rede externa Docker..."
EXTERNAL_NET="${DOCKER_EXTERNAL_NETWORK:-lunaesolutionsback_lunae-network}"
if ! docker network inspect "$EXTERNAL_NET" >/dev/null 2>&1; then
    echo "[deploy-vps] Criando rede externa ${EXTERNAL_NET}..."
    docker network create "$EXTERNAL_NET" >/dev/null
else
    echo "[deploy-vps] Rede externa pronta: ${EXTERNAL_NET}"
fi

echo "[deploy-vps] 3/6 Ajustando permissões de execução dos scripts..."
chmod +x "${ROOT_DIR}/scripts/"*.sh "${ROOT_DIR}/docker/backup/entrypoint.sh" "${ROOT_DIR}/docker/postgres/init-databases.sh"

echo "[deploy-vps] 4/6 Construindo e iniciando containers..."
docker compose up -d --build --remove-orphans

echo "[deploy-vps] 5/6 Aplicando migrations e validando healthcheck..."
for i in $(seq 1 15); do
    if docker compose exec -T api alembic upgrade head; then
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "[deploy-vps] ERRO: Falha ao executar alembic upgrade head." >&2
        exit 1
    fi
    sleep 2
done

for i in $(seq 1 20); do
    if docker compose exec -T api curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        echo "[deploy-vps] API respondendo /health com sucesso!"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "[deploy-vps] ERRO: API não respondeu ao healthcheck a tempo." >&2
        exit 1
    fi
    sleep 2
done

echo "[deploy-vps] 6/6 Configurando cron semanal de atualização e manutenção..."
"${ROOT_DIR}/scripts/setup-auto-update.sh"

echo "[deploy-vps] Deploy concluído! Status dos containers:"
docker compose ps
echo ""
echo "[deploy-vps] Próximo passo: inclua o bloco de docker/nginx/infinity-whatsapp.conf em"
echo "  /root/apps/lunaesolutionsback/nginx/nginx.conf e recarregue o container lunae-nginx."
