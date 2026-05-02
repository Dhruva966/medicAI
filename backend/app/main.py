"""FastAPI entrypoint — mounts routers, configures CORS, initializes DB."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import briefs, evidence, network, satellite, scores, vessels


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ShadowFleet OS",
        description="AI maritime deception detection.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(vessels.router)
    app.include_router(scores.router)
    app.include_router(briefs.router)
    app.include_router(network.router)
    app.include_router(satellite.router)
    app.include_router(evidence.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
