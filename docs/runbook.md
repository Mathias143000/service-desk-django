# Runbook

## Goal

This runbook is the shortest path to starting the service desk stack, validating it, collecting evidence, and exercising backup/restore.

## Start The Stack

### Prepare `.env`

```powershell
python tools/bootstrap_env.py
```

### Build and start

```powershell
docker compose up -d --build
```

### Confirm services

```powershell
docker compose ps
```

Expected core services:

- `db`
- `redis`
- `api`
- `worker`
- `beat` (scheduler lane)
- `nginx`
- `prometheus`
- `alertmanager`
- `grafana`
- `otel-collector`
- `tempo`

## Seed Demo Data

```powershell
docker compose exec -T api python manage.py seed_demo_data
```

The smoke tool can do this automatically with `--seed-demo-data`.

## Run Smoke

```powershell
python tools/smoke_check.py --seed-demo-data
```

What smoke verifies:

- API health is green
- JWT login works
- ticket creation works through the edge
- async notification stub completes
- summary and analytics endpoints respond
- runtime snapshot becomes available
- metrics endpoint exposes service metrics
- Prometheus, Alertmanager, Grafana, and Tempo respond

## Inspect Operational Surfaces

### API

- `http://127.0.0.1:18220/api/docs/`
- `http://127.0.0.1:18220/api/health/`
- `http://127.0.0.1:18220/api/runtime/`
- `http://127.0.0.1:18220/api/metrics/`

### Prometheus

```powershell
Invoke-WebRequest http://127.0.0.1:19220/api/v1/rules | Select-Object -ExpandProperty Content
Invoke-WebRequest http://127.0.0.1:19220/api/v1/alerts | Select-Object -ExpandProperty Content
```

### Alertmanager

```powershell
Invoke-WebRequest http://127.0.0.1:19223/api/v2/alerts | Select-Object -ExpandProperty Content
```

### Grafana

- URL: `http://127.0.0.1:13180`
- Credentials: `admin / admin12345`

### Tempo

```powershell
Invoke-WebRequest http://127.0.0.1:13241/api/search?limit=5 | Select-Object -ExpandProperty Content
```

## Backup And Restore

### Create a backup

```powershell
python tools/backup_postgres.py
```

Default output:

- `artifacts/backups/servicedesk.sql`

### Restore into a clean database

```powershell
python tools/restore_postgres.py --input artifacts/backups/servicedesk.sql
```

Default restore target:

- `servicedesk_restore_check`

### Verify restored data

```powershell
docker compose exec -T db psql -U servicedesk -d servicedesk_restore_check -Atc "SELECT COUNT(*) FROM tickets_ticket;"
```

## Collect Evidence

```powershell
python tools/collect_logs.py
```

Artifacts are written to:

- `artifacts/evidence/compose-ps.txt`
- `artifacts/evidence/compose-config.txt`
- `artifacts/evidence/compose-logs.txt`

## Focused Validation Commands

```powershell
python -m ruff check src tools
python src/manage.py check
python src/manage.py test
docker compose config
python tools/smoke_check.py --seed-demo-data
```

## Shutdown

```powershell
docker compose down -v --remove-orphans
```

## Common Failure Modes

### `DisallowedHost` during metrics scraping

Check that `DJANGO_ALLOWED_HOSTS` includes both `api` and `nginx`.

### Smoke fails waiting for runtime snapshot

Inspect the `beat` container. In this repo it is the dedicated scheduler lane:

```powershell
docker compose logs beat
```

### Tempo search returns no traces

Check `otel-collector` and `tempo` logs:

```powershell
docker compose logs otel-collector tempo
```

### Restore fails

Check that the backup file exists and the target database name is valid:

```powershell
Test-Path artifacts/backups/servicedesk.sql
```
