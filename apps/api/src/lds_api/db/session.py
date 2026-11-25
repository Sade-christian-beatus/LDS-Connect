"""Moteur et sessions SQLAlchemy (mode synchrone : FastAPI exécute les routes dans un pool)."""

from collections.abc import AsyncIterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lds_api.core.config import get_settings

_s = get_settings()
engine = create_engine(
    _s.database_url,
    pool_pre_ping=True,
    future=True,
    # Une page du site appelle l'API plusieurs fois en parallèle : marge pour les pointes
    pool_size=_s.db_pool_size,
    max_overflow=_s.db_max_overflow,
    pool_timeout=10,  # échouer vite plutôt que de laisser s'empiler les requêtes
    # Filet de sécurité : PostgreSQL coupe une transaction oubliée au bout d'une minute
    connect_args={"options": "-c idle_in_transaction_session_timeout=60000"},
)
# close_resets_only=False : une session fermée ne peut plus servir. Si le client abandonne la
# requête, la session est fermée alors que la route peut encore tourner dans son fil ; sans
# cela, la route rouvrirait une transaction que plus personne ne fermerait (connexion perdue).
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False, close_resets_only=False
)


async def get_db() -> AsyncIterator[Session]:
    """Session de la requête, rendue au pool dans tous les cas.

    Dépendance asynchrone à dessein : `finally` s'exécute dans la boucle principale, y compris
    quand le client abandonne la requête pendant une pointe de trafic (une fermeture confiée
    au pool de fils pouvait alors ne jamais avoir lieu). La route elle-même reste synchrone.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
