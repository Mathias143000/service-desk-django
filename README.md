# Service Desk API

## Portfolio Role

This repository is a stateful production-style API workload for the platform portfolio.

Use it when the review should focus on:

- role-aware API behavior and workflow constraints
- SLA-oriented ticket lifecycle
- audit trail, reporting, and operational endpoints
- Docker and CI packaging for a realistic workload
- an application that can be deployed under the larger Kubernetes and platform labs

In the overall portfolio this project is a workload companion, not the primary platform flagship. It shows the kind of service a platform needs to run, expose, observe, and recover.

Небольшой, но собранный service desk на Django REST Framework. Пользователь создает тикет, support берет его в работу, API следит за ролями, SLA и допустимыми переходами статусов, а важные изменения попадают в аудит.

Это API вокруг реального workflow: правила процесса живут в коде явно, operational-метрики доступны через API, а проект удобно поднимать и проверять локально.

## Что умеет API

- JWT-аутентификация (`access` / `refresh`)
- Разделение ролей:
  - `user` работает только со своими тикетами
  - `support` видит и обрабатывает все
- Полный базовый цикл тикета:
  - создание
  - просмотр
  - частичное обновление
  - назначение исполнителя
  - смена статуса и приоритета
- SLA-логика:
  - дедлайн вычисляется автоматически по приоритету
  - `first_response_at` фиксируется при первом взятии в работу
  - `resolved_at` фиксируется при закрытии или отклонении
  - просроченные тикеты можно фильтровать отдельно
- Аудит ключевых изменений:
  - создание тикета
  - смена статуса
  - смена приоритета
  - смена исполнителя
  - обновление полей
- Audit trail по тикету через API
- CSV-экспорт списка тикетов с учетом текущих фильтров
- Summary и analytics endpoints для operational-обзора
- Поиск, фильтрация, сортировка, пагинация
- Healthcheck приложения и базы данных
- OpenAPI schema, Swagger UI и ReDoc
- Docker-конфигурация для быстрого старта
- Demo seed command для наполнения стенда
- CI: lint, Django checks, tests

## Заметки

- API не только хранит данные, но и защищает workflow от неконсистентных состояний.
- SLA-поля и summary/analytics вынесены в отдельный слой, чтобы операционные правила были частью модели, а не “договоренностью”.
- Summary и analytics считаются агрегирующими запросами к БД, чтобы API не тянул все тикеты в память ради operational-метрик.
- Audit trail и export добавлены как часть реального сценария использования, а не как декоративные endpoints.

## Стек

- Python 3.12
- Django 5
- Django REST Framework
- SimpleJWT
- django-filter
- drf-spectacular
- PostgreSQL
- Docker / Docker Compose
- Ruff
- GitHub Actions

## Архитектура

- `tickets.models` - доменные сущности `Ticket` и `AuditLog`
- `tickets.serializers` - валидация и ограничения на уровне API
- `tickets.permissions` - role-aware permission logic
- `tickets.views` - orchestration API-операций
- `tickets.audit` - аудит изменений
- `tickets.sla` - SLA-расчеты и временные метки workflow
- `tickets.workflow` - правила переходов статусов и assignment constraints
- `tickets.reporting` - summary и analytics для operational API
- `tickets.filters` - кастомная фильтрация, включая overdue-сценарии
- `config.settings` - конфигурация через env

## Структура проекта

```text
.
├── src/
│   ├── config/
│   ├── tickets/
│   │   ├── migrations/
│   │   ├── audit.py
│   │   ├── models.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   └── manage.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Быстрый старт

### Docker

```bash
cp .env.example .env
docker compose up --build
```

После старта API доступно на `http://localhost:8000`.

### Локальный запуск

```bash
python -m venv .venv
. .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/manage.py migrate
python src/manage.py runserver
```

Чтобы быстро получить рабочий стенд с пользователями и тикетами:

```bash
python src/manage.py seed_demo_data
```

## Demo

Минимальный сценарий, который удобно показать в README или на интервью:

1. Поднять проект и наполнить его демо-данными:

```bash
cp .env.example .env
docker compose up --build
docker compose exec app python src/manage.py seed_demo_data
```

2. Получить JWT для support-пользователя:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"support","password":"pass12345"}'
```

3. Проверить operational endpoints:

```bash
curl http://localhost:8000/api/health/
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/tickets/summary/
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/tickets/analytics/
```

4. Создать новый тикет и посмотреть audit trail:

```bash
curl -X POST http://localhost:8000/api/tickets/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"VPN is unstable","description":"Reconnect every 10 minutes","priority":"high"}'
```

## Конфигурация

Базовые настройки берутся из `.env.example`.

Для production можно включить HTTPS-настройки через env:

- `DJANGO_SECURE_SSL_REDIRECT=1`
- `DJANGO_SECURE_HSTS_SECONDS=31536000`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=1`
- `DJANGO_SECURE_HSTS_PRELOAD=1`

SLA тоже настраивается через env:

- `TICKET_SLA_LOW_HOURS`
- `TICKET_SLA_MEDIUM_HOURS`
- `TICKET_SLA_HIGH_HOURS`
- `TICKET_SLA_CRITICAL_HOURS`

## Основные эндпойнты

- `POST /api/auth/token/` - получить JWT-токены
- `POST /api/auth/token/refresh/` - обновить access token
- `GET /api/tickets/` - список тикетов
- `POST /api/tickets/` - создать тикет
- `GET /api/tickets/{id}/` - получить тикет
- `PATCH /api/tickets/{id}/` - обновить тикет
- `GET /api/tickets/{id}/audit-log/` - история изменений по тикету
- `GET /api/tickets/export/` - CSV-экспорт видимых тикетов
- `GET /api/tickets/summary/` - сводка по очереди
- `GET /api/tickets/analytics/` - operational-метрики
- `GET /api/health/` - healthcheck приложения и БД
- `GET /api/schema/` - OpenAPI JSON
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc

Удаление тикетов намеренно отключено: `DELETE /api/tickets/{id}/` не поддерживается.

## Примеры ответов

`GET /api/health/`

```json
{
  "status": "ok",
  "database": "ok",
  "timestamp": "2026-03-08T10:00:00Z",
  "version": "1.4.0"
}
```

`GET /api/tickets/summary/`

```json
{
  "visible_tickets": 12,
  "active_tickets": 8,
  "resolved_tickets": 4,
  "unassigned_tickets": 3,
  "unanswered_tickets": 2,
  "overdue_tickets": 1,
  "by_status": {
    "new": 2,
    "in_progress": 6,
    "closed": 3,
    "rejected": 1
  },
  "by_priority": {
    "low": 3,
    "medium": 5,
    "high": 3,
    "critical": 1
  }
}
```

`GET /api/tickets/analytics/`

```json
{
  "avg_first_response_hours": 1.25,
  "avg_resolution_hours": 6.0,
  "resolved_within_sla": 8,
  "resolved_outside_sla": 2,
  "oldest_overdue_hours": 3.5,
  "active_workload_by_assignee": [
    {
      "assigned_to": 3,
      "assigned_to_username": "support",
      "active_tickets": 4
    }
  ]
}
```

## Фильтрация и сортировка

- Фильтры: `status`, `priority`, `assigned_to`, `created_by`
- SLA-фильтры: `is_overdue`, `due_before`, `due_after`
- Поиск: `?search=...` по `title` и `description`
- Сортировка: `created_at`, `updated_at`, `priority`, `status`, `sla_deadline_at`
- Пагинация: `PageNumberPagination`, размер страницы настраивается через env

## Аудит и отчетность

Каждое важное изменение записывается в `AuditLog`, а история доступна через `GET /api/tickets/{id}/audit-log/`.

`GET /api/tickets/export/` отдает CSV с учетом текущих фильтров. Это полезно не только для демо, но и как простой operational reporting без отдельного BI-слоя.

## Workflow Rules

API валидирует несколько явных правил:

- тикет в `in_progress` обязан иметь `assigned_to`
- `closed` и `rejected` нельзя вернуть в `new`
- reopen допускается только в `in_progress`

Это простая, но важная вещь: доменные ограничения становятся частью поведения системы, а не остаются “договоренностью в голове”.

## Проверка качества

Тесты:

```bash
python src/manage.py test
```

Линтинг:

```bash
python -m pip install -r requirements-dev.txt
ruff check src
```

CI в GitHub Actions выполняет:

- `ruff check src`
- `python src/manage.py check`
- `python src/manage.py test`

## Что можно развивать дальше

- уведомления через email / Telegram / Slack
- SLA breach alerts и эскалации
- экспорт отчетов в XLSX / PDF
- отдельный dashboard UI поверх analytics и summary
