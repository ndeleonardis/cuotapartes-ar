"""Clave por consumidor (C11). Cada consumidor manda su clave en el encabezado
X-Clave. Se compara en tiempo constante contra todas, para no dar pistas por
cuánto tarda la respuesta."""

import hmac

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

ENCABEZADO = "X-Clave"
MENSAJE = "Falta la clave o no es válida."


class ClaveInvalida(Exception):
    pass


class Acceso:
    """Dependencia de FastAPI: devuelve el nombre del consumidor o responde 401."""

    def __init__(self, claves: dict[str, str]) -> None:
        self._claves = [(nombre, clave.encode()) for nombre, clave in claves.items()]

    def instalar(self, app: FastAPI) -> None:
        @app.exception_handler(ClaveInvalida)
        async def clave_invalida(_: Request, __: ClaveInvalida) -> JSONResponse:
            return JSONResponse(status_code=401, content={"error": MENSAJE})

    def __call__(self, request: Request) -> str:
        recibida = request.headers.get(ENCABEZADO, "").encode()
        consumidor = None
        for nombre, clave in self._claves:
            if hmac.compare_digest(recibida, clave):
                consumidor = nombre
        if consumidor is None:
            raise ClaveInvalida()
        return consumidor
