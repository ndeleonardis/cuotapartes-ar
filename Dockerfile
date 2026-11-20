# Imagen del servicio. Corre sin privilegios y sin herramientas de desarrollo.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero las dependencias, para que la capa se reuse si solo cambia el código.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev

RUN useradd --system --uid 10001 --no-create-home cuotapartes
USER cuotapartes

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# /salud chequea también la base: si la base no responde, el contenedor queda unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=4).status == 200 else 1)"]

# La configuración (URL_BASE y CLAVES) llega por variables de entorno.
CMD ["uvicorn", "cuotapartes.app:crear_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
