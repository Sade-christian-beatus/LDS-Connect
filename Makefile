# LDS Connect — commandes courantes. `make help` pour la liste.
# Par défaut, tout passe par Docker Compose. Les cibles *-local tournent sans Docker
# (PostgreSQL 16 et Redis installés sur la machine, Python via uv, Node via pnpm).

COMPOSE ?= docker compose
API_EXEC = $(COMPOSE) exec api
API_DIR = apps/api
WEB_DIR = apps/web

.DEFAULT_GOAL := help
.PHONY: help env keys keys-into-env up dev down logs migrate seed test lint e2e shell-db \
        install-local dev-local migrate-local seed-local test-local backup restore purge export

help: ## Affiche cette aide
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[32m%-16s\033[0m %s\n", $$1, $$2}'

env: ## Crée .env à partir de .env.example et y inscrit des clés neuves
	@if [ -f .env ]; then echo ".env existe déjà (rien n'est écrasé)"; \
	 else cp .env.example .env && $(MAKE) --no-print-directory keys-into-env && echo ".env créé"; fi

keys: ## Affiche un jeu de clés neuves (JWT, chiffrement, signature des licences)
	@cd $(API_DIR) && uv run python -m lds_api.cli gen-keys

# Avec uv si disponible, sinon dans le conteneur de l'API (seuls Docker et make sont requis)
keys-into-env:
	@if command -v uv >/dev/null 2>&1; then \
	  cd $(API_DIR) && uv run python -m lds_api.cli gen-keys --write ../../.env; \
	else \
	  $(COMPOSE) build api && \
	  $(COMPOSE) run --rm --no-deps -T -u "$$(id -u):$$(id -g)" -v "$(CURDIR)/.env:/tmp/lds.env" api \
	    python -m lds_api.cli gen-keys --write /tmp/lds.env; \
	fi

# --- Docker ---------------------------------------------------------------
up: ## Lance toute la pile en arrière-plan (API, web, PostgreSQL, Redis, Mailpit, simulateurs)
	$(COMPOSE) up -d --build

dev: ## Lance toute la pile au premier plan (journaux visibles)
	$(COMPOSE) up --build

down: ## Arrête la pile
	$(COMPOSE) down

logs: ## Suit les journaux
	$(COMPOSE) logs -f --tail=100

migrate: ## Applique les migrations de base de données
	$(API_EXEC) alembic upgrade head

seed: ## Charge les données de départ (saison 2027, équipes, comptes de test, joueurs fictifs)
	$(API_EXEC) python -m lds_api.cli seed

test: ## Lance les tests de l'API (pytest) et le lint
	$(COMPOSE) run --rm --no-deps -e TEST_DATABASE_URL=postgresql+psycopg://$${POSTGRES_USER:-lds}:$${POSTGRES_PASSWORD:-lds-dev-password}@postgres:5432/lds_test api sh -c "uv sync --frozen && uv run pytest -q"

lint: ## Vérifie le style (ruff + eslint + TypeScript)
	cd $(API_DIR) && uv run ruff check . && uv run ruff format --check .
	cd $(WEB_DIR) && pnpm lint && pnpm typecheck

e2e: ## Tests de bout en bout (Playwright) — la pile doit tourner et être seedée
	cd $(WEB_DIR) && pnpm e2e

shell-db: ## Ouvre psql sur la base
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-lds} $${POSTGRES_DB:-lds}

# --- Sans Docker --------------------------------------------------------------
install-local: ## Installe les dépendances Python et Node
	cd $(API_DIR) && uv sync
	cd $(WEB_DIR) && pnpm install

dev-local: ## Lance API et web sans Docker
	@echo "API : http://localhost:8000/api/v1/docs — Web : http://localhost:3000"
	@(cd $(API_DIR) && uv run uvicorn lds_api.main:app --reload --port 8000) & \
	 (cd $(WEB_DIR) && pnpm dev) ; wait

migrate-local: ## Applique les migrations sans Docker
	cd $(API_DIR) && uv run alembic upgrade head

seed-local: ## Charge les données de départ sans Docker
	cd $(API_DIR) && uv run python -m lds_api.cli seed

test-local: ## Lance pytest sans Docker
	cd $(API_DIR) && uv run pytest -q

# --- Exploitation -------------------------------------------------------------
backup: ## Sauvegarde PostgreSQL dans ./backups
	./infra/scripts/backup.sh

restore: ## Restaure une sauvegarde : make restore FILE=backups/xxx.dump
	./infra/scripts/restore.sh $(FILE)

purge: ## Efface les données arrivées au terme de leur conservation (DRY=1 pour simuler)
	$(API_EXEC) python -m lds_api.cli purge $(if $(DRY),--dry-run,)

export: ## Export complet des données (JSON + CSV)
	$(API_EXEC) python -m lds_api.cli export --out /app/var/storage/exports
