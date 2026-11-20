"""El servicio HTTP. Todas las respuestas de error tienen la forma {"error": "..."}
y están en español (regla 1)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from cuotapartes.acceso import Acceso
from cuotapartes.config import Configuracion, cargar_configuracion
from cuotapartes.db import BaseDeMercado, BaseSinDatos

MENSAJE_SIN_DATOS = "Servicio sin datos: la base de mercado no responde."


def error(estado: int, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"error": mensaje})


def crear_app(configuracion: Configuracion | None = None) -> FastAPI:
    configuracion = configuracion or cargar_configuracion()
    acceso = Acceso(configuracion.claves_por_consumidor())
    base = BaseDeMercado(configuracion.url_base, configuracion.espera_base_segundos)

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        base.abrir()
        yield
        base.cerrar()

    app = FastAPI(
        title="cuotapartes-ar",
        lifespan=ciclo_de_vida,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.base = base
    acceso.instalar(app)

    @app.exception_handler(BaseSinDatos)
    async def sin_datos(_: Request, __: BaseSinDatos) -> JSONResponse:
        return error(503, MENSAJE_SIN_DATOS)

    @app.exception_handler(HTTPException)
    async def error_http(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error(404, f"No existe la ruta {request.url.path}.")
        if exc.status_code == 405:
            return error(405, f"La ruta {request.url.path} no acepta {request.method}.")
        return error(exc.status_code, str(exc.detail))

    @app.get("/salud")
    def salud() -> dict[str, str]:
        with base.conexion() as conexion:
            conexion.execute("select 1")
        return {"estado": "ok"}

    return app
