# Service Desk API

Production-style Django service desk API packaged as a DevOps portfolio stand.

This repository demonstrates how a stateful business API can be operated behind an edge proxy, split into request and async lanes, instrumented for metrics/logs/traces, and supported by repeatable operator workflows such as smoke checks, evidence collection, and PostgreSQL backup/restore.

## What This Project Demonstrates

- `nginx -> gunicorn -> Django REST API` request path
- `PostgreSQL` as the primary data store
- `Redis` for cache and async runtime support
- `Celery` worker for background notification flow
- dedicated scheduler lane for runtime snapshots
- non-root application container runtime
- `Prometheus + Grafana + Alertmanager` for metrics and alerting
- `OpenTelemetry + Tempo` for traces
- JSON logs and repeatable evidence collection
- compose-based local demo that behaves like a believable production stack

## Portfolio Role

This is the secure production-style API workload in the portfolio.

Its job is to show what a believable stateful service looks like when it is deployed under a platform with:

- edge proxying
- async/background lanes
- metrics, traces, and alerting
- smoke tooling and evidence collection
- backup and restore workflow

In the overall portfolio this repository works best as a workload companion to the larger platform labs, not as the primary platform flagship by itself.

## Architecture

```text
client
  -> nginx:18220
    -> gunicorn / Django API
      -> PostgreSQL
      -> Redis
      -> Celery worker
      -> scheduler lane (run_scheduler)

API / worker / scheduler
  -> OTel Collector
    -> Tempo

Prometheus
  -> scrape nginx-facing API metrics
  -> evaluate alerts
    -> Alertmanager

Grafana
  -> Prometheus
  -> Alertmanager
  -> Tempo
```

More detail is in [docs/architecture.md](./docs/architecture.md).

## Stack Components

| Component | Purpose |
| --- | --- |
| `nginx` | Edge proxy, rate limiting point, stable entry path |
| `api` | Django REST API served by Gunicorn |
| `worker` | Celery worker for notification stub tasks |
| `beat` | Dedicated scheduler lane running `python manage.py run_scheduler` |
| `db` | PostgreSQL primary datastore |
| `redis` | Cache and broker/backend support for Celery |
| `prometheus` | Metrics scraping and alert evaluation |
| `alertmanager` | Alert routing and active alert surface |
| `grafana` | Dashboards and operator visibility |
| `otel-collector` | OTLP intake and trace forwarding |
| `tempo` | Trace storage and search |

## Quick Start

### 1. Prepare local environment

```powershell
python tools/bootstrap_env.py
```

### 2. Start the full stack

```powershell
docker compose up -d --build
```

### 3. Run the smoke flow

```powershell
python tools/smoke_check.py --seed-demo-data
```

Expected result:

```json
{"status": "ok", "ticket_id": 7}
```

### 4. Open operator surfaces

- API edge: `http://127.0.0.1:18220`
- Swagger: `http://127.0.0.1:18220/api/docs/`
- Health: `http://127.0.0.1:18220/api/health/`
- Runtime: `http://127.0.0.1:18220/api/runtime/`
- Metrics: `http://127.0.0.1:18220/api/metrics/`
- Prometheus: `http://127.0.0.1:19220`
- Alertmanager: `http://127.0.0.1:19223`
- Grafana: `http://127.0.0.1:13180` (`admin` / `admin12345`)
- Tempo API: `http://127.0.0.1:13241`

## Demo Flow

### Flow 1: API runtime

1. Get a JWT token through `/api/auth/token/`.
2. Create a ticket through `/api/tickets/`.
3. Watch the worker asynchronously stamp `notification_stub_sent_at`.
4. Review `/api/tickets/summary/` and `/api/tickets/analytics/`.

### Flow 2: Operations visibility

1. Open `/api/runtime/` and confirm queue depth plus cached runtime snapshot.
2. Open Grafana and inspect the service desk overview dashboard.
3. Open Prometheus and check alert/rule state.
4. Query Tempo and confirm traces are present.

### Flow 3: Data safety

1. Create a backup with `python tools/backup_postgres.py`.
2. Restore into a clean database with `python tools/restore_postgres.py --input artifacts/backups/servicedesk.sql`.
3. Verify restored ticket count in PostgreSQL.

## Operator Toolkit

### Backup and restore

```powershell
python tools/backup_postgres.py
python tools/restore_postgres.py --input artifacts/backups/servicedesk.sql
```

### Evidence collection

```powershell
python tools/collect_logs.py
```

### Focused validation

```powershell
python -m ruff check src tools
python tools/hardening_check.py
python src/manage.py check
python src/manage.py test
docker compose config
python tools/smoke_check.py --seed-demo-data
```

## CI

GitHub Actions validates the project in two layers:

- `test`: Ruff, Django checks, hardening policy check, test suite
- `compose-smoke`: compose config, container build/start, full smoke flow, diagnostics on failure

See [ci.yml](./.github/workflows/ci.yml).
See [docs/hardening.md](./docs/hardening.md) for the third-wave workload hardening scope.

## Why The Scheduler Lane Exists

The compose service is still named `beat`, but for the local demo stack it intentionally runs `python manage.py run_scheduler` instead of standalone Celery Beat. This keeps periodic runtime snapshot refresh deterministic in the current minimal environment while preserving the same operational role: a dedicated scheduler lane outside the request path.

## Portfolio Visible Ready

This repository is intentionally packaged as a showcase:

- README with quick demo flow
- architecture note
- operator runbook
- smoke tooling
- backup/restore workflow
- observability surfaces
- hardening policy check
- known limitations section

## Known Limitations

- The scheduler lane is implemented through a dedicated management command instead of pure standalone Celery Beat.
- The application image runs as a non-root user; third-party service images use their vendor defaults.
- Local TLS via `mkcert`, SBOM generation, and signed images are still polish items rather than DoD blockers.

## Next Polish Items

- rename the `beat` service to `scheduler` for clearer naming
- add local TLS with `mkcert`
- add image signing and SBOM generation
- add load generation and degradation drills beyond smoke coverage
