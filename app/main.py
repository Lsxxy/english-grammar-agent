from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import init_db
from app.routes import admin, feishu
from app.scheduler import build_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    scheduler = build_scheduler(settings)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="English Grammar Agent", version="0.1.0", lifespan=lifespan)
app.include_router(admin.router)
app.include_router(feishu.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
