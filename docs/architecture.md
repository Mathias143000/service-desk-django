# Architecture

## Purpose

`service-desk-api` is the portfolio project for production-style API operations. It demonstrates how a stateful Django service can be packaged with edge routing, async workloads, observability, and data-safety workflows.

## Component View

```text
                        +-------------------+
                        |      Grafana      |
                        +---------+---------+
                                  |
                 +----------------+----------------+
                 |                                 |
        +--------v---------+              +--------v---------+
        |    Prometheus    |              |      Tempo       |
        +--------+---------+              +--------+---------+
                 |                                 ^
                 |                                 |
                 |                         +-------+--------+
                 |                         | OTel Collector |
                 |                         +-------+--------+
                 |                                 ^
                 |                                 |
+--------+  +---v----+   +-------------------+     |
| client |->| nginx  |-->| api (gunicorn)    |-----+
+--------+  +--------+   +----+--------------+
                            |        |
                            |        +--------------------------+
                            |                                   |
                     +------v-------+                    +------v------+
                     | PostgreSQL   |                    | Redis       |
                     +--------------+                    +------+------+ 
                                                                  |
                                               +------------------+------------------+
                                               |                                     |
                                      +--------v--------+                   +--------v---------+
                                      | Celery worker   |                   | scheduler lane   |
                                      | notification    |                   | run_scheduler    |
                                      +-----------------+                   +------------------+
```

## Request Flow

1. Client traffic enters through `nginx` on `:18220`.
2. `nginx` proxies requests to Gunicorn inside the `api` container.
3. Django serves JWT auth, ticket CRUD, summary, analytics, export, health, runtime, and metrics endpoints.
4. Request data is persisted in PostgreSQL.
5. Runtime support such as caching and Celery broker/result backend uses Redis.

## Async Flow

1. Ticket create/update actions schedule `send_ticket_notification_stub`.
2. The task is published to Redis-backed Celery queues.
3. The `worker` container executes the notification stub outside the request path.
4. The ticket record is updated with `notification_stub_sent_at`.

## Periodic Operations Flow

1. The dedicated scheduler lane runs `python manage.py run_scheduler`.
2. It periodically executes `refresh_operational_snapshot`.
3. Snapshot data is cached for operator visibility.
4. `/api/runtime/` exposes queue depth and runtime snapshot.
5. `/api/metrics/` rehydrates snapshot-derived gauges before Prometheus scrapes them.
6. Prometheus evaluates rules and forwards firing alerts to Alertmanager.

## Observability Flow

1. API, worker, and scheduler emit OTLP spans to the OTel Collector.
2. Collector forwards traces to Tempo.
3. Prometheus scrapes application metrics through the API edge.
4. Grafana reads from Prometheus, Alertmanager, and Tempo.
5. JSON logs can be collected through `python tools/collect_logs.py`.

## Operator Interfaces

- `http://127.0.0.1:18220/api/health/`
- `http://127.0.0.1:18220/api/ready/`
- `http://127.0.0.1:18220/api/live/`
- `http://127.0.0.1:18220/api/runtime/`
- `http://127.0.0.1:18220/api/metrics/`
- `http://127.0.0.1:19220` for Prometheus
- `http://127.0.0.1:19223` for Alertmanager
- `http://127.0.0.1:13180` for Grafana
- `http://127.0.0.1:13241` for Tempo API

## Reliability Notes

- The request path is separated from background work.
- Metrics, alerts, and traces are available in the local demo.
- Backup/restore is part of the operator story and is not left implicit.
- The current scheduler implementation favors deterministic local behavior over strict “pure Celery Beat” purity.
