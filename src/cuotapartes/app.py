"""El servicio HTTP. Todas las respuestas de error tienen la forma {"error": "..."}
y están en español (regla 1)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from cuotapartes.acceso import Acceso
from cuotapartes.config import Configuracion, cargar_configuracion
from cuotapartes.consultas import (
    PedidoInvalido,
    leer_codigos,
    leer_rango,
    serie,
    ultima_planilla,
    ultimo_valor,
)
from cuotapartes.db import BaseDeMercado, BaseSinDatos
from cuotapartes.modelos import EstadoDelServicio, RespuestaSerie, RespuestaUltimo

MENSAJE_SIN_DATOS = "Servicio sin datos: la base de mercado no responde."

registro = logging.getLogger("cuotapartes")


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
        return error(exc.status_code, "El pedido no se pudo atender.")

    @app.exception_handler(PedidoInvalido)
    async def pedido_invalido(_: Request, exc: PedidoInvalido) -> JSONResponse:
        return error(422, str(exc))

    @app.exception_handler(RequestValidationError)
    async def validacion(_: Request, __: RequestValidationError) -> JSONResponse:
        return error(422, "El pedido no es válido.")

    @app.exception_handler(Exception)
    async def inesperado(request: Request, exc: Exception) -> JSONResponse:
        # Al registro va el detalle; al consumidor, nunca (puede tener datos internos).
        registro.error("Error inesperado en %s", request.url.path, exc_info=exc)
        return error(500, "Error interno del servicio.")

    @app.get("/salud")
    def salud() -> dict[str, str]:
        with base.conexion() as conexion:
            conexion.execute("select 1")
        return {"estado": "ok"}

    v1 = APIRouter(prefix="/v1", dependencies=[Depends(acceso)])

    @v1.get("/ultimo", response_model=RespuestaUltimo)
    def ultimo(codigos: str | None = None) -> RespuestaUltimo:
        pedidos = leer_codigos(codigos)
        with base.conexion() as conexion:
            return RespuestaUltimo(resultados=ultimo_valor(conexion, pedidos))

    @v1.get("/serie", response_model=RespuestaSerie)
    def serie_de_valores(
        codigos: str | None = None, desde: str | None = None, hasta: str | None = None
    ) -> RespuestaSerie:
        pedidos = leer_codigos(codigos)
        inicio, fin = leer_rango(desde, hasta)
        with base.conexion() as conexion:
            return RespuestaSerie(
                desde=inicio, hasta=fin, series=serie(conexion, pedidos, inicio, fin)
            )

    @v1.get("/estado", response_model=EstadoDelServicio)
    def estado_del_servicio() -> EstadoDelServicio:
        with base.conexion() as conexion:
            return ultima_planilla(conexion)

    app.include_router(v1)
    app.state.router_v1 = v1
    return app
