# Production Deployment Guide — Chanakya Research Commons

This guide documents how to deploy **Chanakya Research Commons** on a single **Ubuntu 24.04 Linux VPS** using Docker Compose (`docker-compose.yml` + `docker-compose.prod.yml`) and **Caddy** for automatic HTTPS/TLS, without modifying application code.

---

## 1. Minimum Server & Resource Requirements

Verified live container footprint (`docker stats`): **~970 MiB idle** (`backend` 735 MiB with PyTorch CPU + `all-MiniLM-L6-v2`, `minio` 139 MiB, `postgres` 87 MiB, `frontend` 9 MiB; peaks ~1.5–1.8 GB during ETL/evaluation).

- **Recommended VPS:** Ubuntu 24.04 LTS · **2+ vCPU · 4 GB RAM · 40–60 GB SSD** (approx. \$6–\$18/mo on Hetzner/DigitalOcean/AWS Lightsail, or a campus university VM).
- **Important:** Do **not** deploy the backend on 512 MB RAM free tiers—`torch` + `all-MiniLM-L6-v2` requires ≥ 1.5–2 GB container memory (`mem_limit: 2g` configured in `docker-compose.prod.yml`).

---

## 2. Pre-Deployment Security & Environment Checklist

1. Copy `.env.example` to `.env` (never commit `.env` to Git):
   ```bash
   cp .env.example .env
   ```
2. Generate strong secrets:
   ```bash
   python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
   python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
   python3 -c "import secrets; print('MINIO_ROOT_PASSWORD=' + secrets.token_urlsafe(24))"
   ```
3. Configure `.env` for production:
   - `APP_ENV=production` and `DEBUG=false` (disables `/docs`, `/redoc`, `/openapi.json` and enables generic 500 error masking).
   - `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD` set to strong random values (`docker-compose.prod.yml` enforces mandatory `:?` checks and `validate_production_security()` refuses startup if weak/default secrets or wildcard CORS remain).
   - `CORS_ORIGINS=https://commons.example.edu` (exact public HTTPS origin—never `*`).
   - `VITE_API_BASE_URL=` **left empty** so the compiled React bundle uses relative `/api/*` paths routed cleanly through Nginx.
   - `ENABLE_SCHEDULER=true` (keep `true` on a single backend instance; PostgreSQL advisory lock `pg_try_advisory_lock(7842109)` prevents overlapping scheduled jobs if multiple workers/instances ever run).

---

## 3. Single Linux VPS Production Deployment (Recommended)

### Persistent Storage Layout
- `postgres_data` (Docker named volume): PostgreSQL 16 database (`/var/lib/postgresql/data`)
- `minio_data` (Docker named volume): MinIO S3 Bronze lake (`chanakya-raw-lake`)
- `hf_cache` (Docker named volume): Persisted `all-MiniLM-L6-v2` weights (~88 MB, avoids re-downloading on restart)
- `./data` & `./data_warehouse` (host mounts): Silver/Gold Parquet Star Schema & DuckDB warehouse (`chanakya_dw.duckdb`)

### Launch Production Stack
```bash
# 1. Validate rendered production config (fails fast if any required secret is missing)
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet

# 2. Build and start hardened stack (postgres, minio, backend are internal-only; frontend binds 127.0.0.1:3000)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. Verify all 4 containers are healthy
docker compose ps

# 4. Run initial bootstrap (schema, real ingestion, embeddings, PageRank, DuckDB warehouse)
docker compose exec backend python scripts/bootstrap_all.py
```

### Enable HTTPS Reverse Proxy (Caddy)
```bash
sudo apt-get update && sudo apt-get install -y caddy
sudo cp Caddyfile.example /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile   # Replace commons.example.edu with your domain
sudo systemctl reload caddy
```
Firewall (`ufw`): allow only `22/tcp` (SSH), `80/tcp` (HTTP ACME challenge), and `443/tcp` (HTTPS). Because `docker-compose.prod.yml` removes host port bindings on `postgres`, `minio`, and `backend`, none of those internal ports are exposed publicly.

---

## 4. Backup & Recovery Procedures

### PostgreSQL Backup & Verified Clean Restore
```bash
# Nightly compressed backup (verified clean restore with --clean --if-exists --no-owner)
docker compose exec -T postgres pg_dump --clean --if-exists --no-owner -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "backup_pg_$(date +%F).sql.gz"

# Restore PostgreSQL from backup (stop backend first for write consistency)
docker compose stop backend
gunzip -c backup_pg_YYYY-MM-DD.sql.gz | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
docker compose start backend

# Rebuild DuckDB/Parquet Star Schema Warehouse after restore
docker compose exec backend python -c "from backend.app.core.database import SessionLocal; from data_warehouse.etl import build_warehouse; db=SessionLocal(); print(build_warehouse(db)); db.close()"
```

### MinIO Bronze Lake Backup & Recovery
```bash
# Snapshot the MinIO Docker volume to a compressed archive
docker run --rm -v dmw-project_minio_data:/data:ro -v "$(pwd)/backups:/backup" alpine \
  tar czf "/backup/backup_minio_$(date +%F).tar.gz" -C /data .

# Restore MinIO volume from archive (stop minio during restore)
docker compose stop minio
docker run --rm -v dmw-project_minio_data:/data -v "$(pwd)/backups:/backup:ro" alpine \
  sh -c "rm -rf /data/* && tar xzf /backup/backup_minio_YYYY-MM-DD.tar.gz -C /data"
docker compose start minio
```

---

## 5. Upgrades, Rollbacks, Monitoring & Troubleshooting

### Upgrade Procedure
```bash
git pull origin main
# Take a pre-upgrade PostgreSQL snapshot before rebuilding
docker compose exec -T postgres pg_dump --clean --if-exists --no-owner -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "pre_upgrade_$(date +%F_%H%M).sql.gz"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps
```

### Rollback Procedure
```bash
git checkout <previous-known-good-commit>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# If schema/data rollback is also needed, restore pre_upgrade_*.sql.gz using Section 4
```

### Monitoring & Logs
- Container health: `docker compose ps` (all 4 services have active healthchecks).
- Structured app & admin audit logs (`ADMIN_AUDIT role_change ...`): `docker compose logs -f --tail=100 backend` (JSON log rotation capped at 10 MB × 5 files in `docker-compose.prod.yml`).
- Nginx proxy & rate-limit logs (`HTTP 429` bursts): `docker compose logs -f --tail=100 frontend`.

### Common Troubleshooting
- **Startup fails with `Production startup blocked: ...`**: One of `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `CORS_ORIGINS`, or `DEBUG=false` still holds a dev default in `.env`.
- **Frontend calls `localhost:8000` after custom build**: Ensure `VITE_API_BASE_URL` is empty (`""`) in `.env` before running `docker compose up --build`.
- **Admin ingestion returns `504` on slow external APIs**: `frontend/nginx.conf` sets `proxy_read_timeout 180s`; trigger smaller `per_query` batches (`8–15`) or run inside the container via `docker compose exec backend python ...`.
- **Cutover from Synthetic Activity to Live University Accounts:** Preserve real papers (`papers.is_synthetic = FALSE`), purge synthetic users/activity (`is_synthetic = TRUE`) in a transaction before public launch, and trigger `POST /api/analytics/rebuild-warehouse`.
