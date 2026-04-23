# Workload Hardening

This repository is a stateful workload companion for the platform labs, so the third hardening wave focuses on runtime readiness and operator evidence instead of adding more business features.

## What Is Covered

- application container runs as a non-root user
- compose stack includes edge, API, worker, scheduler, database, cache, metrics, alerts, traces, and dashboards
- API, worker, and scheduler have health checks or runtime dependency checks
- CI runs Ruff, Django checks, repo-local hardening policy, unit tests, compose validation, and smoke checks
- smoke tooling exercises auth, ticket creation, metrics, and the async notification path
- backup/restore and evidence collection tools are documented as operator workflows

## Local Validation

```powershell
python -m ruff check src tools
python tools\hardening_check.py
python src\manage.py check
python src\manage.py test
docker compose config
python tools\smoke_check.py --seed-demo-data
```

The hardening check writes a local report to:

```text
artifacts/hardening/hardening-report.json
```

The report is ignored by Git because it is runtime evidence, not source code.

## Deliberate Trade-Offs

- Local TLS and image signing stay out of this wave so the repo remains a workload demo, not a second platform flagship.
- The scheduler lane keeps the compose service name `beat` for compatibility, while the command clearly runs the deterministic scheduler management command.
- Vendor images such as PostgreSQL, Redis, Nginx, Prometheus, Grafana, Alertmanager, Tempo, and the OTel Collector are not rebuilt in this repo.

## Remaining Backlog

- SBOM and image signing
- local TLS with `mkcert`
- degradation drill for Redis or worker outage
- lightweight load profile with documented expectations
