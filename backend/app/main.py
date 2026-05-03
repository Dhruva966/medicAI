"""FastAPI entrypoint — mounts routers, configures CORS, initializes DB."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.clients import aisstream, copernicus, equasis, gfw, ofac
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
    def health() -> dict[str, Any]:
        s = get_settings()
        return {
            "status": "ok",
            "live_data_mode": s.live_data_mode,
            "clients": {
                "ofac": ofac.status(),
                "aisstream": aisstream.status(),
                "gfw": gfw.status(),
                "copernicus": copernicus.status(),
                "equasis": equasis.status(),
            },
        }

    return app


app = create_app()
