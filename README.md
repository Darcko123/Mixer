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
uv run alembic upgrade head
uv run fastapi dev

# 3. Web → http://localhost:4200 (proxy /api → :8000)
cd frontend
npm install
npm start
```

La API lee `DATABASE_URL` del entorno; por defecto usa `postgresql+psycopg://mixer:mixer@localhost:5432/mixer`, que coincide con `docker-compose.yml`.

## Calidad

Lint y formato (ruff, Prettier, ESLint) corren con [pre-commit](https://pre-commit.com) desde la raíz del repo (requiere `npm install` en `frontend/`):

```bash
uvx pre-commit install          # una vez: ejecuta los hooks en cada commit
uvx pre-commit run --all-files  # manualmente sobre todo el repo
```

Pruebas y build:

```bash
# backend/ (requiere la BD levantada; las pruebas usan una BD aparte, `mixer_test`)
uv run pytest
uv run alembic check   # los modelos y las migraciones no divergen

# frontend/
npx ng test --watch=false && npm run build
```

La CI ejecuta lo mismo en cada push: `.github/workflows/pre-commit.yml` y `.github/workflows/test.yml`.
