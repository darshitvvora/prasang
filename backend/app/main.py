"""FastAPI application factory."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

import app.models  # noqa: F401  - registers every ORM mapper before first use
from app.artists.router import router as artists_router
from app.auth.router import router as auth_router
from app.auth.supertokens_setup import init_supertokens
from app.config import Settings, get_settings
from app.errors import install_error_handlers
from app.health import router as health_router
from app.leads.router import router as leads_router
from app.locations.router import router as locations_router
from app.media.router import router as media_router
from app.reviews.router import router as reviews_router
from app.search.router import router as search_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_for_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    init_supertokens(settings)
    app = FastAPI(title="Prasang API", version="1.0.0", docs_url=f"{API_PREFIX}/docs", openapi_url=f"{API_PREFIX}/openapi.json")
    install_error_handlers(app)
    app.include_router(health_router)
    for router in (auth_router, locations_router, reviews_router, media_router, search_router, artists_router, leads_router):
        app.include_router(router, prefix=API_PREFIX)
    app.add_middleware(get_middleware())  # SuperTokens routes under /api/v1/auth + session handling
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", *get_all_cors_headers()],
    )
    return app


app = create_app()
