from fastapi import FastAPI

from app.routers import inventory

app = FastAPI(title="Mixer API")
app.include_router(inventory.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
