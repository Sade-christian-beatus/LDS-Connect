"""Point d'entrée de l'API LDS Connect."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lds_api.api.v1 import auth, fixtures, licences, live, public, registry, sheets
from lds_api.core.config import get_settings
from lds_api.core.errors import install_handlers

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LDS Connect API",
        description="API de la plateforme numérique de la Ligue de la Souveraineté",
        version="0.1.0",
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_handlers(app)

    v1 = APIRouter(prefix=API_PREFIX)
    for module in (auth, public, registry, licences, fixtures, sheets, live):
        v1.include_router(module.router)
    app.include_router(v1)

    # GET et HEAD : les sondes de supervision et répartiteurs de charge utilisent souvent HEAD
    @app.api_route(f"{API_PREFIX}/health", methods=["GET", "HEAD"], tags=["système"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
