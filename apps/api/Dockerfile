FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# uv installé depuis PyPI (un seul registre à autoriser sur un réseau restreint)
RUN pip install --no-cache-dir "uv>=0.5,<1"
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY . .
RUN uv sync --frozen --no-dev

RUN useradd --create-home lds && mkdir -p /app/var/storage && chown -R lds /app/var
USER lds
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "lds_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
