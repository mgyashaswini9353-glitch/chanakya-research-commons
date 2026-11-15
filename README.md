# Chanakya Research Commons

Docker-first foundation for a university research collaboration platform. This Phase 1 repository contains the local service foundation only; application features and synthetic datasets are not implemented yet.

## Requirements

- Git
- Docker Desktop on Windows/macOS, or Docker Engine with the Docker Compose plugin on Linux

Python, Node.js, PostgreSQL, Redis, MinIO, and DuckDB do not need to be installed on the host.

## Start the application

1. Clone the repository and open its directory.
2. Copy `.env.example` to `.env` and set local passwords/credentials. The example uses obvious local-only values; replace them before exposing services beyond your computer.
3. Build and start the stack:

   ```sh
   docker compose up --build
   ```

4. Open <http://localhost:5173>. The API health endpoint is <http://localhost:8000/health>; MinIO Console is <http://localhost:9001>.

PowerShell copy command:

```powershell
Copy-Item .env.example .env
```

Linux/macOS (or Git Bash) copy command:

```sh
cp .env.example .env
```

Compose builds the React development server, API, and worker images and downloads the database, Redis, and MinIO images. The first run needs internet access and can take several minutes. Browser requests to `/api` are proxied by the frontend container to the backend using the Compose network; backend services address one another by Compose service name.

## Stop, restart, and reset

- Stop containers without removing them or their data: `docker compose stop`
- Start stopped containers: `docker compose start`
- Remove containers/network while preserving named volumes: `docker compose down`
- Rebuild after code or dependency changes: `docker compose up --build`
- **Destructive full reset:** `docker compose down -v` removes the PostgreSQL, MinIO, and analytics volumes permanently. Use only when you intend to erase all local application data.

PostgreSQL and MinIO persist in named Docker volumes. Parquet/analytics storage is also mounted persistently for the API and worker. Do not remove volumes when you only mean to stop or restart the application.

## Services

Compose starts a React/Vite frontend, FastAPI backend, background worker, PostgreSQL 16 with pgvector, Redis, and MinIO. DuckDB is a Python library in both Python images, not a separate service. Health checks gate the API and worker on their dependencies. The API and worker currently expose health/readiness only; product requirements F1–F9 and data generation are out of scope for this foundation.

All settings are supplied through `.env`. Never commit `.env` or put real secrets in source control. The included credentials are for local development only.
