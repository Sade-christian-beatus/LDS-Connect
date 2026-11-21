"""Point d'entrée de l'API LDS Connect."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lds_api.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LDS Connect API",
        description="API de la plateforme numérique de la Ligue de la Souveraineté",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["système"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
