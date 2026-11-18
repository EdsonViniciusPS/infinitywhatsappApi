# Infinity WhatsApp API

API WhatsApp em **Python (FastAPI)** construída sobre a **Evolution API v2**, com suporte multi-tenant (API Key e JWT), logs em PostgreSQL, cache/filas em Redis e deploy pronto para **VPS** com Docker Compose integrado à rede oficial `lunaesolutionsback_lunae-network` (`lunae-nginx`).

## Recursos Cobertos

- **Auth & Multi-tenancy** (`/api/v1/auth`): gestão de tenants, emissão de `X-API-Key` e troca por JWT Bearer.
- **Instâncias** (`/api/v1/instances`): criar, listar, conectar (QR Code / Pairing Code), status, reiniciar, logout, deletar, presença e configurações.
- **Mensagens** (`/api/v1/messages/{instance}`): texto, mídia (imagem/vídeo/documento), áudio narrado (PTT), sticker, localização, contato, reação, enquete, lista, botões, status/stories, editar, apagar e marcar como lida.
- **Chats & Contatos** (`/api/v1/chats/{instance}`): verificar números no WhatsApp, foto/perfil comercial, listar chats/mensagens/contatos, arquivar, bloquear e presença.
- **Grupos** (`/api/v1/groups/{instance}`): criar, listar, metadados, assunto/descrição/foto, participantes, convites, permissões, mensagens temporárias e sair do grupo.
- **Webhooks** (`/api/v1/webhooks`): receptor global da Evolution API + encaminhamento assíncrono com assinatura HMAC-SHA256 e retry por instância.
- **Integrações** (`/api/v1/integrations/{instance}`): Typebot, Chatwoot, OpenAI e Dify.
- **Gemini AI** (`/api/v1/ai`): integração via SDK oficial `google-genai` (**Interactions API**) com modelo padrão **`gemini-4-hydrogen`**, memória conversacional multi-turno por contato no Redis (`previous_interaction_id`), envio direto com IA (`/{instance}/send`), limpeza de memória (`DELETE /{instance}/memory/{number}`) e auto-resposta no webhook (`/{instance}/config`).
- **Backups & Manutenção (`/api/v1/backups`)**: criação de snapshots `.json.gz`, listagem, download, restauração idempotente, limpeza por retenção e ciclo automático de 7 dias para limpeza de logs/memória (`POST /api/v1/backups/maintenance`).

## Desenvolvimento Local (com `uv`)

```bash
uv sync --extra dev
cp .env.example .env
uv run uvicorn app.main:app --reload
```

Acesse a documentação interativa em `http://localhost:8000/docs`.

### Rodar testes

```bash
uv run pytest
```

## Deploy na VPS (`lunaesolutionsback_lunae-network` + `lunae-nginx`)

O `docker-compose.yml` foi preparado para conviver sem conflito de portas com a infraestrutura atual da VPS (`lunae-nginx` nas portas 80/443 e demais stacks na porta 8000):

- O serviço `api` sobe como `infinity-whatsapp-api` expondo apenas a porta interna `8000` dentro da rede interna isolada (`infinity_whatsapp_internal`) e da rede externa oficial `lunaesolutionsback_lunae-network`.
- `postgres`, `redis`, `evolution-api` (`evoapicloud/evolution-api:v2.3.7`) e `backup` ficam isolados em `infinity_whatsapp_internal` com nomes prefixados (`infinity-whatsapp-*`).

### Passo a passo na VPS

1. Aponte o subdomínio escolhido (ex: `infinity-api.lunaesolutions.com.br`) para o IP da VPS (`72.61.219.197`) via registro A.
2. Clone o projeto na VPS (ex: `/root/apps/infinitywhatsappApi`) e configure o `.env`:
   ```bash
   cp .env.example .env
   # Preencha DOMAIN, WEBHOOK_PUBLIC_URL e GEMINI_API_KEY
   # Os demais segredos (JWT_SECRET_KEY, ADMIN_MASTER_KEY, EVOLUTION_WEBHOOK_SECRET,
   # POSTGRES_PASSWORD e EVOLUTION_API_KEY) serão gerados automaticamente pelo script caso estejam como change-me-*
   ```
3. Execute o deploy automatizado (garante a rede `lunaesolutionsback_lunae-network`, sobe os containers, aplica migrations Alembic, valida `/health` e ativa o cron semanal):
   ```bash
   chmod +x scripts/*.sh docker/backup/entrypoint.sh docker/postgres/init-databases.sh
   ./scripts/deploy-vps.sh
   ```
4. Publique o domínio no proxy reverso `lunae-nginx` usando o template `docker/nginx/infinity-whatsapp.conf`:
   - Adicione primeiro o bloco `server` da porta `80` (com `location /.well-known/acme-challenge/`) em `/root/apps/lunaesolutionsback/nginx/nginx.conf`, ajustando `server_name` para o seu domínio.
   - Valide e recarregue o Nginx:
     ```bash
     docker exec lunae-nginx nginx -t && docker exec lunae-nginx nginx -s reload
     ```
   - Emita o certificado SSL via Certbot usando o webroot compartilhado com o `lunae-nginx`:
     ```bash
     certbot certonly --webroot -w /root/apps/lunaesolutionsback/nginx/certbot/www -d SEU_DOMINIO
     ```
   - Adicione o bloco `server` da porta `443` de `docker/nginx/infinity-whatsapp.conf` em `/root/apps/lunaesolutionsback/nginx/nginx.conf` e recarregue o Nginx novamente:
     ```bash
     docker exec lunae-nginx nginx -t && docker exec lunae-nginx nginx -s reload
     ```
5. Crie o primeiro tenant e API Key usando o header `X-Master-Key`:
   ```bash
   curl -X POST https://SEU_DOMINIO/api/v1/auth/tenants \
     -H "X-Master-Key: SEU_ADMIN_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name": "Cliente 1", "email": "cliente@empresa.com"}'
   ```

## Persistência, Backup e Atualização sem Perda de Dados na VPS

O `docker-compose.yml` foi blindado contra reinicializações da VPS e atualizações de versão:

- **Volumes com nomes fixos**: `infinity_postgres_data`, `infinity_redis_data` e `infinity_evolution_instances` garantem que os dados e sessões do WhatsApp nunca se percam nem mudem de referência.
- **Desligamento gracioso e Redis persistente**: `stop_grace_period: 30s` em `postgres`, `redis` e `evolution-api`, além de `AOF` (`appendfsync everysec`) + snapshot (`--save 60 1`) no Redis.
- **Backup automático contínuo (container `backup`)**: gera arquivos completos em `./backups/full_backup_<UTC>.tar.gz` (contendo dumps dos bancos `infinity_api` e `evolution`, sessões `/evolution/instances` e dados do Redis) a cada `BACKUP_INTERVAL_SECONDS` (padrão: 6 horas) e remove arquivos mais antigos que `BACKUP_RETENTION_DAYS` (padrão: 7 dias).
- **Manutenção e reciclagem de memória a cada 7 dias**:
  - **Backend FastAPI**: executa automaticamente a cada `MAINTENANCE_INTERVAL_SECONDS` (`604800`s = 7 dias) gerando snapshot preventivo, removendo logs antigos (`message_logs` e `webhook_deliveries` > `LOG_RETENTION_DAYS`), liberando memória (`gc.collect()` + Redis `MEMORY PURGE`) e reciclando workers Gunicorn (`--max-requests 2000`).
  - **Containers & Logs**: rotação automática de logs Docker (`10m`, máximo 3 arquivos por serviço), compactação automática do AOF do Redis e limite de heap na Evolution API (`NODE_OPTIONS="--max-old-space-size=1024"`).

### Comandos na VPS

- **Primeiro deploy completo e agendamento semanal**:
  ```bash
  ./scripts/deploy-vps.sh
  ```
- **Atualizar a API sem perder dados** (faz backup preventivo, `git pull --ff-only`, rebuild dos containers preservando volumes, `alembic upgrade head`, limpeza de logs + `VACUUM ANALYZE`, `docker image/builder prune` e valida `/health`):
  ```bash
  ./scripts/update-vps.sh
  ```
- **Gerar backup manual imediato**:
  ```bash
  ./scripts/backup.sh
  ```
- **Restaurar um backup completo (`.tar.gz`)**:
  ```bash
  ./scripts/restore.sh backups/full_backup_YYYYMMDD_HHMMSS.tar.gz
  ```
- **Endpoints administrativos de backup e manutenção (`/api/v1/backups`, header `X-Master-Key`)**:
  - `GET /api/v1/backups` — lista backups `.tar.gz` e `.json.gz`.
  - `POST /api/v1/backups/snapshot` — gera snapshot imediato `.json.gz` do banco da API.
  - `GET /api/v1/backups/{filename}/download` — baixa um backup.
  - `POST /api/v1/backups/{filename}/restore` — restaura `Tenant`, `ApiKey` e `Instance` a partir de um snapshot `.json.gz`.
  - `DELETE /api/v1/backups/prune` — remove arquivos expirados conforme `BACKUP_RETENTION_DAYS`.
  - `POST /api/v1/backups/maintenance` — dispara manualmente o ciclo de manutenção e limpeza de memória.
