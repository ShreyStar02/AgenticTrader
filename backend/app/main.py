"""AgenticTrader FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.logging_config import get_logger
from app.scheduler import shutdown_scheduler, start_scheduler

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s (%s)", settings.app_name, settings.environment)
    bootstrap()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs", "api": "/api"}
