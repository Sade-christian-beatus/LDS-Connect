"""Erreurs métier : renvoyées au client en 422 avec un message lisible en français."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class BusinessError(ValueError):
    """Règle métier non respectée. `code` permet au client d'afficher une aide ciblée."""

    def __init__(self, message: str, *, code: str = "business_rule", details=None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class NotFound(LookupError):
    def __init__(self, what: str = "Ressource") -> None:
        super().__init__(f"{what} introuvable")


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def _business(_: Request, exc: BusinessError) -> JSONResponse:
        body = {"detail": exc.message, "code": exc.code}
        if exc.details is not None:
            body["details"] = exc.details
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "Conflit : cette donnée existe déjà (doublon)", "code": "conflict"},
        )
