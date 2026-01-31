Service Desk API (Django + DRF)

Backend API для управления тикетами (мини service desk / task tracker).

Stack:
- Django
- Django REST Framework
- PostgreSQL
- JWT (SimpleJWT)
- Docker Compose
- Swagger (drf-spectacular)

Run:
docker compose up --build

Swagger:
http://localhost:8000/api/schema/swagger-ui/

Auth:
POST /api/token/
POST /api/token/refresh/

Main endpoints:
GET /api/tickets/
POST /api/tickets/
GET /api/tickets/{id}/
PATCH /api/tickets/{id}/
DELETE /api/tickets/{id}/
