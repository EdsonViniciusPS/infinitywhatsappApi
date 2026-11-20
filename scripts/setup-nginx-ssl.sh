#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DEFAULT_DOMAIN="api.lunaesolutions.com.br"
VPS_IP="72.61.219.197"
NGINX_CONF="/root/apps/lunaesolutionsback/nginx/nginx.conf"
CERTBOT_WEBROOT="/root/apps/lunaesolutionsback/nginx/certbot/www"
NGINX_CONTAINER="lunae-nginx"

if [ ! -f .env ]; then
    cp .env.example .env
fi

echo "[setup-nginx-ssl] 1/6 Normalizando DOMAIN e WEBHOOK_PUBLIC_URL no .env..."
DOMAIN_RAW="$(grep -E '^DOMAIN=' .env | tail -n 1 | cut -d'=' -f2- || true)"
DOMAIN="$(printf '%s' "$DOMAIN_RAW" | tr -d '; \t\r"'\''')"
if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "api.seudominio.com.br" ]; then
    DOMAIN="$DEFAULT_DOMAIN"
fi
WEBHOOK_URL="https://${DOMAIN}/api/v1/webhooks/evolution"

python3 - "$DOMAIN" "$WEBHOOK_URL" <<'PY'
import pathlib
import re
import sys

domain, webhook_url = sys.argv[1], sys.argv[2]
env_path = pathlib.Path(".env")
text = env_path.read_text(encoding="utf-8")

def upsert(src: str, key: str, val: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(src):
        return pattern.sub(f"{key}={val}", src)
    return src.rstrip("\n") + f"\n{key}={val}\n"

text = upsert(text, "DOMAIN", domain)
text = upsert(text, "WEBHOOK_PUBLIC_URL", webhook_url)
env_path.write_text(text, encoding="utf-8")
PY
echo "[setup-nginx-ssl] Domínio configurado no .env: ${DOMAIN}"

echo "[setup-nginx-ssl] 2/6 Verificando apontamento DNS de ${DOMAIN}..."
if ! python3 - "$DOMAIN" "$VPS_IP" <<'PY'
import socket
import sys

domain, expected_ip = sys.argv[1], sys.argv[2]
try:
    infos = socket.getaddrinfo(domain, None, socket.AF_INET)
    ips = sorted({info[4][0] for info in infos})
except socket.gaierror:
    print(f"[setup-nginx-ssl] ERRO: O domínio '{domain}' ainda não resolve no DNS.", file=sys.stderr)
    sys.exit(1)

if expected_ip not in ips:
    print(
        f"[setup-nginx-ssl] ERRO: '{domain}' resolve para {ips}, mas o IP esperado da VPS é {expected_ip}.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"[setup-nginx-ssl] DNS OK: {domain} -> {', '.join(ips)}")
PY
then
    echo "" >&2
    echo "Crie um registro DNS tipo A no provedor do domínio lunaesolutions.com.br:" >&2
    echo "  Tipo: A | Nome: api | Valor: ${VPS_IP}" >&2
    echo "Aguarde a propagação e execute ./scripts/setup-nginx-ssl.sh novamente." >&2
    exit 1
fi

echo "[setup-nginx-ssl] 3/6 Verificando/emitindo certificado SSL com Certbot..."
mkdir -p "$CERTBOT_WEBROOT"
CERT_FULLCHAIN="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
if [ ! -f "$CERT_FULLCHAIN" ]; then
    certbot certonly --webroot \
        -w "$CERTBOT_WEBROOT" \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --register-unsafely-without-email
    echo "[setup-nginx-ssl] Certificado emitido com sucesso em /etc/letsencrypt/live/${DOMAIN}/"
else
    echo "[setup-nginx-ssl] Certificado já existente em ${CERT_FULLCHAIN}."
fi

echo "[setup-nginx-ssl] 4/6 Configurando ${NGINX_CONF} (com backup automático)..."
if [ ! -f "$NGINX_CONF" ]; then
    echo "[setup-nginx-ssl] ERRO: Arquivo não encontrado: ${NGINX_CONF}" >&2
    exit 1
fi

BACKUP_CONF="${NGINX_CONF}.bak.$(date +%Y%m%d_%H%M%S)"
cp "$NGINX_CONF" "$BACKUP_CONF"

if ! python3 - "$NGINX_CONF" "$DOMAIN" <<'PY'
import pathlib
import re
import sys

conf_path = pathlib.Path(sys.argv[1])
domain = sys.argv[2]
content = conf_path.read_text(encoding="utf-8")

if re.search(rf"server_name\s+[^;]*\b{re.escape(domain)}\b", content):
    print(f"[setup-nginx-ssl] Bloco para '{domain}' já existe em {conf_path}; mantendo configuração atual.")
    sys.exit(0)

http_match = re.search(r"(^|\s)http\s*\{", content, re.MULTILINE)
if not http_match:
    print(f"[setup-nginx-ssl] ERRO: Bloco 'http {{ ... }}' não encontrado em {conf_path}.", file=sys.stderr)
    sys.exit(1)

brace_start = content.index("{", http_match.start())
depth = 0
in_single = False
in_double = False
in_comment = False
escaped = False
close_idx = None

for idx in range(brace_start, len(content)):
    ch = content[idx]
    if in_comment:
        if ch == "\n":
            in_comment = False
        continue
    if escaped:
        escaped = False
        continue
    if in_single:
        if ch == "\\":
            escaped = True
        elif ch == "'":
            in_single = False
        continue
    if in_double:
        if ch == "\\":
            escaped = True
        elif ch == '"':
            in_double = False
        continue

    if ch == "#":
        in_comment = True
    elif ch == "'":
        in_single = True
    elif ch == '"':
        in_double = True
    elif ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            close_idx = idx
            break

if close_idx is None:
    print(f"[setup-nginx-ssl] ERRO: Fechamento do bloco 'http' não encontrado em {conf_path}.", file=sys.stderr)
    sys.exit(1)

server_block = f"""
    server {{
        listen 80;
        server_name {domain};

        location /.well-known/acme-challenge/ {{
            root /var/www/certbot;
        }}

        location / {{
            return 301 https://$host$request_uri;
        }}
    }}

    server {{
        listen 443 ssl;
        http2 on;
        server_name {domain};

        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

        client_max_body_size 50M;

        add_header X-Content-Type-Options nosniff always;
        add_header X-Frame-Options DENY always;
        add_header Referrer-Policy strict-origin-when-cross-origin always;

        resolver 127.0.0.11 valid=30s;

        location / {{
            set $infinity_api_upstream http://infinity-whatsapp-api:8000;
            proxy_pass $infinity_api_upstream;
            proxy_http_version 1.1;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 30s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
        }}
    }}
"""

new_content = content[:close_idx].rstrip() + "\n" + server_block + content[close_idx:]
conf_path.write_text(new_content, encoding="utf-8")
print(f"[setup-nginx-ssl] Bloco server para '{domain}' adicionado em {conf_path}.")
PY
then
    cp "$BACKUP_CONF" "$NGINX_CONF"
    exit 1
fi

echo "[setup-nginx-ssl] 5/6 Testando e recarregando container ${NGINX_CONTAINER}..."
if ! docker exec "$NGINX_CONTAINER" nginx -t; then
    echo "[setup-nginx-ssl] ERRO no nginx -t; restaurando backup ${BACKUP_CONF}..." >&2
    cp "$BACKUP_CONF" "$NGINX_CONF"
    exit 1
fi
docker exec "$NGINX_CONTAINER" nginx -s reload

echo "[setup-nginx-ssl] 6/6 Validando HTTPS em https://${DOMAIN}/health..."
sleep 2
if curl -fsS "https://${DOMAIN}/health"; then
    echo ""
    echo "[setup-nginx-ssl] Tudo pronto! API publicada em https://${DOMAIN}"
else
    echo ""
    echo "[setup-nginx-ssl] AVISO: Nginx recarregado, mas https://${DOMAIN}/health falhou. Verifique 'docker ps' e 'docker logs infinity-whatsapp-api'." >&2
    exit 1
fi
