"""FastAPI application entrypoint for the O2C Graph Query API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine
from app.models.base import Base
from app.routes.graph import router as graph_router
from app.routes.health import router as health_router
from app.routes.query import router as query_router

import app.models  # noqa: F401 — register all ORM models with Base.metadata

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create tables on startup; dispose of the engine pool on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")
    yield
    await engine.dispose()
    logger.info("Database engine disposed.")


app = FastAPI(
    title="O2C Graph Query API",
    description="Graph-based data modelling and NL query system for SAP Order-to-Cash data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(graph_router)
app.include_router(query_router)
