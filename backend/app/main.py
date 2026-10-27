from fastapi import FastAPI

from app.routers import inventory, recipes

app = FastAPI(title="Mixer API")
app.include_router(inventory.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
