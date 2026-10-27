# Mixer

Aplicación web de mixología: registra los ingredientes que tienes y te recomienda qué cócteles preparar y qué comprar. Ver [PLAN.md](PLAN.md).

Stack: Angular · FastAPI · PostgreSQL.

## Requisitos

- Docker con Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- Node 22.22+ (o 24.15+)

## Arranque en desarrollo

```bash
# 1. Base de datos
docker compose up -d db

# 2. API → http://localhost:8000 (docs en /docs)
cd backend
uv sync
uv run fastapi dev

# 3. Web → http://localhost:4200 (proxy /api → :8000)
cd frontend
npm install
npm start
```

La API lee `DATABASE_URL` del entorno; por defecto usa `postgresql+psycopg://mixer:mixer@localhost:5432/mixer`, que coincide con `docker-compose.yml`.

## Calidad

```bash
# backend/
uv run ruff check . && uv run ruff format --check . && uv run pytest

# frontend/
npm run lint && npm run format:check && npx ng test --watch=false && npm run build
```

La CI (`.github/workflows/ci.yml`) ejecuta lo mismo en cada push.
